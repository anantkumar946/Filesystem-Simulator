"""
Streamlit dashboard: File System Performance Analyzer
Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import time
import os
import tempfile
import plotly.express as px
from pathlib import Path
from typing import Dict, Any, Optional

st.set_page_config(page_title="FS Analyzer", layout="wide")

# ---------- Utilities ----------
DEFAULT_FS = ["ext4", "NTFS", "FAT32"]

def human_size(nbytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if nbytes < 1024.0:
            return f"{nbytes:3.1f} {unit}"
        nbytes /= 1024.0
    return f"{nbytes:.1f} PB"

# ---------- Synthetic benchmark ----------
def synthetic_fs_test(fs_name: str, size_bytes: int, iterations: int = 3) -> Dict[str, Any]:
    """
    Create temp files of given size, measure write and read times.
    Small deterministic variation emulates FS differences for demonstration.
    """
    rng = np.random.default_rng(sum(ord(c) for c in fs_name))
    write_times, read_times = [], []
    work_dir = tempfile.mkdtemp(prefix=f"fs_{fs_name}_")

    scale_map = {"ext4": 0.92, "NTFS": 1.05, "FAT32": 1.15}
    scale = scale_map.get(fs_name, 1.0)

    for it in range(iterations):
        fname = os.path.join(work_dir, f"test_{fs_name}_{it}.bin")
        data_chunk = b"x" * 1024
        chunks = max(1, size_bytes // len(data_chunk))

        # Write
        start = time.perf_counter()
        with open(fname, "wb") as f:
            for _ in range(chunks):
                f.write(data_chunk)
        time.sleep(scale * rng.uniform(0.0005, 0.002))
        write_times.append((time.perf_counter() - start) * scale)

        # Read
        start = time.perf_counter()
        with open(fname, "rb") as f:
            _ = f.read()
        time.sleep(scale * rng.uniform(0.0002, 0.001))
        read_times.append((time.perf_counter() - start) * scale)

        try:
            os.remove(fname)
        except OSError:
            pass

    try:
        os.rmdir(work_dir)
    except OSError:
        pass

    return {
        "File System": fs_name,
        "Size": human_size(size_bytes),
        "Iterations": iterations,
        "Avg Write (s)": round(float(np.mean(write_times)), 6),
        "Avg Read (s)": round(float(np.mean(read_times)), 6),
        "Min Write (s)": round(float(np.min(write_times)), 6),
        "Max Write (s)": round(float(np.max(write_times)), 6),
        "Min Read (s)": round(float(np.min(read_times)), 6),
        "Max Read (s)": round(float(np.max(read_times)), 6),
    }

# ---------- Summary generator ----------
def generate_summary(df: pd.DataFrame) -> str:
    df = df.copy()
    df["total"] = df["Avg Write (s)"] + df["Avg Read (s)"]
    best = df.loc[df["total"].idxmin()]
    worst = df.loc[df["total"].idxmax()]
    lines = [
        f"🏆 **Best:** {best['File System']} — combined avg {best['total']:.4f}s",
        f"🐢 **Slowest:** {worst['File System']} — combined avg {worst['total']:.4f}s",
    ]
    if best["Avg Write (s)"] < worst["Avg Write (s)"] and best["Avg Read (s)"] < worst["Avg Read (s)"]:
        lines.append(f"{best['File System']} has lower latency for both reads and writes.")
    else:
        lines.append("Read vs write performance differs — see charts above.")
    return "  \n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
#  SIDEBAR — Settings
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Settings")

    fs_to_test = st.multiselect("File Systems", DEFAULT_FS, default=DEFAULT_FS)
    size_mb = st.slider("File size (MB)", 1, 64, 1)
    iterations = st.slider("Iterations", 1, 10, 3)

    st.divider()
    run_btn = st.button("▶  Run Benchmark", use_container_width=True, type="primary")

    st.divider()
    st.caption("Built-in synthetic benchmark — results emulate FS behaviour for demonstration.")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN PAGE
# ══════════════════════════════════════════════════════════════════════════════
st.title("📂 File System Performance Analyzer")
st.caption("Compare EXT4, NTFS & FAT32 — read/write latency, throughput and timing spread.")

# Run tests when button clicked
if run_btn:
    if not fs_to_test:
        st.warning("Select at least one file system in the sidebar.")
    else:
        size_bytes = size_mb * 1024 * 1024
        results = []
        progress = st.progress(0, text="Running benchmarks...")
        for i, fs in enumerate(fs_to_test):
            progress.progress((i) / len(fs_to_test), text=f"Testing {fs}...")
            results.append(synthetic_fs_test(fs, size_bytes, iterations))
        progress.progress(1.0, text="Done!")
        time.sleep(0.3)
        progress.empty()

        st.session_state["results"] = pd.DataFrame(results)
        st.success(f"Benchmark complete — {len(fs_to_test)} file system(s), {iterations} iterations each.")

# ── Display results ──────────────────────────────────────────────────────────
if "results" in st.session_state:
    df = st.session_state["results"]

    # ── Metric cards ──
    cols = st.columns(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        with cols[i]:
            st.metric(row["File System"], f"{row['Avg Write (s)']:.4f}s write", f"{row['Avg Read (s)']:.4f}s read")

    st.divider()

    # ── Charts side-by-side ──
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Avg Read / Write")
        melted = df.melt(
            id_vars=["File System"],
            value_vars=["Avg Write (s)", "Avg Read (s)"],
            var_name="Operation",
            value_name="Seconds",
        )
        fig1 = px.bar(melted, x="File System", y="Seconds", color="Operation",
                      barmode="group", color_discrete_sequence=["#6366f1", "#22d3ee"])
        fig1.update_layout(margin=dict(t=10, b=10), height=320, legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        st.subheader("Write Spread (min → max)")
        fig2 = px.scatter(df, x="Min Write (s)", y="Max Write (s)", text="File System",
                          color="File System", size_max=14,
                          color_discrete_sequence=["#f43f5e", "#a78bfa", "#34d399"])
        fig2.update_traces(textposition="top center", marker=dict(size=12))
        fig2.update_layout(margin=dict(t=10, b=10), height=320)
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Data table ──
    with st.expander("📋 Full results table", expanded=False):
        st.dataframe(df, use_container_width=True, hide_index=True)

    # ── Summary ──
    st.subheader("Summary")
    st.markdown(generate_summary(df))

else:
    # Landing state
    st.info("👈 Configure settings in the sidebar and click **Run Benchmark** to start.")

    with st.expander("ℹ️  About this project"):
        st.markdown("""
**Cross-Platform File System Simulator** — an educational tool that emulates
FAT32, EXT4, and NTFS file systems and benchmarks their performance.

| Component | Role |
|-----------|------|
| `VirtualDisk` | Block-level storage with bitmap allocation |
| `FAT32` | Linked FAT chain allocation |
| `EXT4` | Inode table + journaling simulation |
| `NTFS` | Master File Table (MFT) |
| `Perf / Fragmentation` | Timing & disk fragmentation metrics |

**CLI mode:** `python main.py`  
**Dashboard:** `streamlit run app.py`
""")
