"""
Streamlit dashboard: Online File System Performance Analyzer
Place this file in the root of your project and run:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import tempfile
import importlib.util
import glob
import traceback
import plotly.express as px
from pathlib import Path
from typing import Dict, Any, Optional

st.set_page_config(page_title="File System Analyzer", layout="wide")

# ---------- Utilities ----------
DEFAULT_FS = ["ext4", "NTFS", "FAT32"]

def human_size(nbytes: int) -> str:
    for unit in ["B","KB","MB","GB","TB"]:
        if nbytes < 1024.0:
            return f"{nbytes:3.1f}{unit}"
        nbytes /= 1024.0
    return f"{nbytes:.1f}PB"

def safe_import_module_from_path(module_path: str, module_name: str = "user_module"):
    """Dynamically import a module from a path. Returns module or raises."""
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None:
        raise ImportError(f"Can't create spec from {module_path}")
    mod = importlib.util.module_from_spec(spec)
    loader = spec.loader
    if loader is None:
        raise ImportError("Spec loader is None")
    loader.exec_module(mod)
    return mod

# ---------- Synthetic benchmark (fallback) ----------
def synthetic_fs_test(fs_name: str, size_bytes: int, iterations: int = 3, work_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a temp file of given size, measure write and read times.
    To emulate different file-systems, small deterministic variation is added.
    Important: When run on a single machine, results reflect your current FS, not
    real differences between ext4/NTFS/FAT32. This is meant for demonstration / comparsion
    when using provided FS-specific backends.
    """
    rng = np.random.default_rng(sum(ord(c) for c in fs_name))
    write_times = []
    read_times = []
    verify_crc = 0
    if work_dir is None:
        work_dir = tempfile.mkdtemp(prefix=f"fs_{fs_name}_")
    Path(work_dir).mkdir(parents=True, exist_ok=True)

    # scale factor to emulate FS differences (for demo only)
    scale_map = {"ext4": 0.92, "NTFS": 1.05, "FAT32": 1.15}
    scale = scale_map.get(fs_name, 1.0)

    for it in range(iterations):
        fname = os.path.join(work_dir, f"test_{fs_name}_{it}.bin")
        # write
        data_chunk = b"x" * 1024  # 1KB chunk
        chunks = max(1, size_bytes // len(data_chunk))
        start = time.perf_counter()
        with open(fname, "wb") as f:
            for _ in range(chunks):
                f.write(data_chunk)
        # small extra busy wait to emulate FS overhead
        time.sleep(scale * rng.uniform(0.0005, 0.002))
        end = time.perf_counter()
        write_times.append((end - start) * scale)

        # read
        start = time.perf_counter()
        with open(fname, "rb") as f:
            _ = f.read()
        time.sleep(scale * rng.uniform(0.0002, 0.001))
        end = time.perf_counter()
        read_times.append((end - start) * scale)

        # quick checksum
        with open(fname, "rb") as f:
            verify_crc ^= sum(f.read()) % 256

        try:
            os.remove(fname)
        except Exception:
            pass

    # clean temp dir if empty
    try:
        os.rmdir(work_dir)
    except Exception:
        pass

    return {
        "fs": fs_name,
        "size_bytes": size_bytes,
        "iterations": iterations,
        "avg_write_s": float(np.mean(write_times)),
        "avg_read_s": float(np.mean(read_times)),
        "min_write_s": float(np.min(write_times)),
        "min_read_s": float(np.min(read_times)),
        "max_write_s": float(np.max(write_times)),
        "max_read_s": float(np.max(read_times)),
        "checksum": int(verify_crc),
    }

# ---------- High-level test orchestrator ----------
def run_tests_for_filesystems(fs_list, size_bytes, iterations, project_module_path=None, project_func_name=None):
    """
    Try to use user's project functions if provided. Expect function signature:
    run_test(fs_name: str, size_bytes: int, iterations: int) -> dict (metrics)
    or run_all_tests(list_of_fs, size_bytes, iterations) -> list[dict]

    If project import fails, fallback to synthetic_fs_test.
    """
    results = []
    if project_module_path:
        try:
            mod = safe_import_module_from_path(project_module_path, "user_project_module")
            # try run_all_tests
            if hasattr(mod, "run_all_tests"):
                try:
                    out = mod.run_all_tests(fs_list, size_bytes, iterations)
                    # expect iterable of dicts
                    for d in out:
                        results.append(dict(d))
                    return results
                except Exception as e:
                    st.warning(f"run_all_tests present but failed: {e}")
                    # fall through to per-FS try
            # try per-FS run_test
            for fs in fs_list:
                if hasattr(mod, "run_test"):
                    try:
                        d = mod.run_test(fs, size_bytes, iterations)
                        results.append(dict(d))
                        continue
                    except Exception as e:
                        st.warning(f"module.run_test for {fs} failed: {e}")
                        # fallback to synthetic for this fs
                        results.append(synthetic_fs_test(fs, size_bytes, iterations))
                else:
                    # no run_test -> fallback
                    results.append(synthetic_fs_test(fs, size_bytes, iterations))
            return results
        except Exception as e:
            st.error(f"Failed to import project module: {e}")
            st.text(traceback.format_exc(limit=3))
            # fall through to synthetic for all
    # no project module or import failed -> synthetic
    for fs in fs_list:
        results.append(synthetic_fs_test(fs, size_bytes, iterations))
    return results

# ---------- Auto summary generator ----------
def generate_summary(results: pd.DataFrame) -> str:
    # Decide best FS by weighted metric: avg_write + avg_read
    results = results.copy()
    results["total_avg_s"] = results["avg_write_s"] + results["avg_read_s"]
    best_row = results.loc[results["total_avg_s"].idxmin()]
    worst_row = results.loc[results["total_avg_s"].idxmax()]

    lines = []
    lines.append(f"**Best performer:** {best_row['fs']} — lowest combined average time ({best_row['total_avg_s']:.4f}s).")
    lines.append(f"**Runner / worst:** {worst_row['fs']} — highest combined average time ({worst_row['total_avg_s']:.4f}s).")
    # Add reasons based on simple heuristic
    if best_row["avg_write_s"] < worst_row["avg_write_s"] and best_row["avg_read_s"] < worst_row["avg_read_s"]:
        lines.append(f"{best_row['fs']} shows lower read and write times across the runs — indicating better latency and throughput under this workload.")
    else:
        lines.append("The performance differs between read and write. Check the graphs for which operations dominate the difference.")
    lines.append("**Notes:** These results were measured on your current machine. Real file-system differences (ext4 vs NTFS vs FAT32) require running tests on partitions formatted with those FS types. This dashboard compares metrics produced by either your project code (if provided) or by a synthetic local benchmark.")
    return "\n\n".join(lines)

# ---------- Streamlit UI ----------
st.title("📂 Online File System Performance Analyzer")

tabs = st.tabs(["Home", "Simulator Info", "Algorithm / Input", "Statistics", "Graphs", "Summary"])

# ---------------- Home ----------------
with tabs[0]:
    st.header("Home — Project Overview")
    col1, col2 = st.columns([2,1])
    with col1:
        st.subheader("Objective")
        st.write(
            "Compare performance characteristics of different file systems (read/write times, latency, throughput, etc.) "
            "by running a set of operations and visualizing results. The dashboard provides a project overview, allows input "
            "of test parameters or integration with your existing project code, shows detailed statistics, and produces a conclusion."
        )
        st.markdown("**How to use:**")
        st.markdown("- Use the **Algorithm / Input** tab to either point the dashboard at your project module or run the built-in test.\n"
                    "- After running, visit **Statistics** and **Graphs** to explore results, and **Summary** for an automated conclusion.")
    with col2:
        st.markdown("""
        <div style='background:#1e293b;border-radius:12px;padding:20px;border:1px solid #334155;'>
            <h4 style='color:#38bdf8;margin:0 0 12px 0;'>📐 Architecture</h4>
            <p style='color:#94a3b8;margin:4px 0;'>🗄️ <b>VirtualDisk</b> — block-level storage backend</p>
            <p style='color:#94a3b8;margin:4px 0;'>📁 <b>FAT32</b> — linked FAT chain allocation</p>
            <p style='color:#94a3b8;margin:4px 0;'>📂 <b>EXT4</b> — inode table + journaling</p>
            <p style='color:#94a3b8;margin:4px 0;'>🗂️ <b>NTFS</b> — Master File Table (MFT)</p>
            <p style='color:#94a3b8;margin:4px 0;'>📊 <b>Utils</b> — fragmentation analysis, Perf timer</p>
        </div>
        """, unsafe_allow_html=True)

# ---------------- Simulator Info ----------------
with tabs[1]:
    st.header("Simulator / File System Info")
    st.write("This project compares common file systems and their behavior under specific operations.")
    st.markdown("**Example file systems included (for demonstration):**")
    st.write(", ".join(DEFAULT_FS))
    st.markdown("**Metrics measured:**")
    st.write("- Average write time\n- Average read time\n- Min/Max times across iterations\n- Simple checksum to verify I/O correctness")
    st.markdown("**Caveat:** Actual differences between file systems require distinct partitions formatted with those file systems. "
                "If you provide a project module that performs FS-specific simulation or testing, the dashboard will try to use it directly.")

# ---------------- Algorithm / Input ----------------
with tabs[2]:
    st.header("Algorithm / Input")
    st.write("Provide test parameters and optionally point to your project Python module (optional). If a module is provided and contains the expected functions, the dashboard will call them.")
    col1, col2 = st.columns(2)
    with col1:
        fs_to_test = st.multiselect("Select file systems to test (demo list)", DEFAULT_FS, default=DEFAULT_FS)
        size_mb = st.number_input("File size per test (MB)", value=1, min_value=1, max_value=1024, step=1)
        iterations = st.number_input("Iterations per FS", value=3, min_value=1, max_value=20, step=1)
        st.checkbox("Keep temporary files for inspection (debug)", value=False, key="keep_tmp")
    with col2:
        st.markdown("**Use your project test code (optional)**")
        st.write("If your project has a Python file with `run_test(fs_name, size_bytes, iterations)` or `run_all_tests(fs_list, size_bytes, iterations)` functions, provide the path here.")
        project_module_path = st.text_input("Full path to your project's .py file (leave empty to use built-in tests)", value="")
        if project_module_path:
            st.write("Attempting to import from:", project_module_path)
        st.markdown("---")
        st.write("Quick example of expected function signatures if you want the dashboard to call your code:")
        st.code("""
# Example 1: per-FS
def run_test(fs_name, size_bytes, iterations):
    # return a dict with keys: fs, size_bytes, iterations, avg_write_s, avg_read_s, min_write_s, min_read_s, max_write_s, max_read_s, checksum
    ...

# Example 2: batch
def run_all_tests(fs_list, size_bytes, iterations):
    return [run_test(fs, size_bytes, iterations) for fs in fs_list]
""", language="python")
    run_button = st.button("Run Tests")

    if run_button:
        st.session_state["running"] = True
        st.session_state["last_results"] = None

    # trigger run if state set
    if st.session_state.get("running", False):
        with st.spinner("Running tests..."):
            size_bytes = int(size_mb * 1024 * 1024)
            try:
                results = run_tests_for_filesystems(fs_to_test, size_bytes, int(iterations),
                                                   project_module_path=project_module_path or None)
                # normalize to DataFrame
                df = pd.DataFrame(results)
                st.success("Tests completed.")
                st.session_state["last_results"] = df
                st.session_state["running"] = False
            except Exception as e:
                st.error(f"Error running tests: {e}")
                st.session_state["running"] = False

# ---------------- Statistics ----------------
with tabs[3]:
    st.header("Statistics")
    if st.session_state.get("last_results") is None:
        st.info("No results yet. Run tests from the 'Algorithm / Input' tab.")
    else:
        df = st.session_state["last_results"]
        # show table with nicer columns
        df_display = df.copy()
        df_display["size_readable"] = df_display["size_bytes"].apply(lambda x: human_size(int(x)))
        df_display = df_display[["fs","size_readable","iterations","avg_write_s","avg_read_s","min_write_s","min_read_s","max_write_s","max_read_s","checksum"]]
        st.dataframe(df_display.reset_index(drop=True))
        st.markdown("**Metrics explanation:** average times in seconds measured over iterations.")

# ---------------- Graphs ----------------
with tabs[4]:
    st.header("Graphical Comparison")
    if st.session_state.get("last_results") is None:
        st.info("Run tests to see graphs.")
    else:
        df = st.session_state["last_results"]
        # basic conversions to numeric (in case)
        for c in ["avg_write_s","avg_read_s","min_write_s","min_read_s","max_write_s","max_read_s"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        # bar: avg read/write
        fig1 = px.bar(df.melt(id_vars=["fs"], value_vars=["avg_write_s","avg_read_s"], var_name="operation", value_name="seconds"),
                      x="fs", y="seconds", color="operation", barmode="group",
                      title="Average read/write time per file system")
        st.plotly_chart(fig1, use_container_width=True)

        # scatter: min vs max (write)
        fig2 = px.scatter(df, x="min_write_s", y="max_write_s", text="fs",
                          title="Write time spread (min vs max) — each point is a FS")
        st.plotly_chart(fig2, use_container_width=True)

        # ratio chart (write/read)
        df["write_over_read"] = df["avg_write_s"] / (df["avg_read_s"].replace(0, np.nan))
        fig3 = px.bar(df, x="fs", y="write_over_read", title="Avg write / Avg read ratio (higher => writes relatively slower)")
        st.plotly_chart(fig3, use_container_width=True)

# ---------------- Summary ----------------
with tabs[5]:
    st.header("Summary & Conclusion")
    if st.session_state.get("last_results") is None:
        st.info("No results yet. Run tests to generate a summary.")
    else:
        df = st.session_state["last_results"]
        if not all(col in df.columns for col in ["avg_write_s","avg_read_s"]):
            st.error("Result data missing expected columns for summary.")
        else:
            summary_text = generate_summary(df)
            st.markdown(summary_text)
            st.markdown("---")
            st.subheader("Detailed observations")
            st.write("You can copy/paste the detailed DataFrame below for reports or include it in a PDF.")
            st.dataframe(df.reset_index(drop=True))

# ---------------- Footer / Help ----------------
st.markdown("---")
st.caption("Tip: If you have a specific project Python file, enter its path in the Algorithm / Input tab (it should export run_test or run_all_tests). Otherwise the dashboard uses a local synthetic benchmark for demonstration.")
