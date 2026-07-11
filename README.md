# 🧠 Cross-Platform File System Simulator

> A Python-based educational simulator that **emulates FAT32, EXT4, and NTFS** file systems and analyzes how each handles **storage allocation, fragmentation, and performance** — with both a CLI interface and an interactive Streamlit dashboard.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-red?logo=streamlit&logoColor=white)
![Pytest](https://img.shields.io/badge/Tests-Pytest-green?logo=pytest&logoColor=white)
![License](https://img.shields.io/badge/License-Educational-lightgrey)

---

## 🚀 Features

- ✅ **Three file system simulations** — FAT32 (linked chain), EXT4 (inodes + journaling), NTFS (Master File Table)
- ✅ **Virtual disk backend** — block-level storage with bitmap-based allocation
- ✅ **File operations** — `create`, `write`, `read`, `delete`, `list`, `info`
- ✅ **Fragmentation analysis** — per-FS fragmentation level and largest free run
- ✅ **Performance metrics** — write/read timing with `Perf` utility class
- ✅ **Streamlit dashboard** — interactive UI with charts, statistics table, and summary
- ✅ **Synthetic benchmark fallback** — built-in benchmarks run even without custom project code
- ✅ **Modular architecture** — easy to extend with new file systems

---

## ⚠️ Important Caveat

> The synthetic benchmark in `app.py` runs all tests on **your current machine's actual file system**.
> True FAT32 / EXT4 / NTFS differences require separate disk partitions formatted with those file systems.
> The simulator faithfully models **allocation behavior and metadata structures** — but real hardware I/O timings reflect only your current machine.

---

## 🧱 Project Structure

```
OS/
├── main.py                        # CLI entry point (interactive REPL)
├── app.py                         # Streamlit web dashboard
├── requirements.txt               # Python dependencies
│
├── filesystems/                   # File system implementations
│   ├── __init__.py                # Package exports (FAT32, Ext4, NTFS)
│   ├── base_filesystem.py         # Abstract base class
│   ├── fat32.py                   # FAT32 simulator (linked FAT chain)
│   ├── ext4.py                    # EXT4 simulator (inodes + journaling)
│   └── ntfs.py                    # NTFS simulator (Master File Table)
│
├── storage/
│   └── virtual_disk.py            # Block-level virtual disk (bitmap allocator)
│
├── utils/
│   ├── fragmentation.py           # Fragmentation metrics (level, largest run)
│   └── performance_metrics.py     # Perf timer class + timeit decorator
│
└── tests/
    └── test_filesystem.py         # Pytest unit tests
```

---

## ⚙️ Setup & Installation

**Requirements:** Python 3.10+

```bash
# 1. Clone the repository
git clone https://github.com/your-username/OS.git
cd OS

# 2. (Optional but recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt
```

---

## ▶️ Running the Project

### Option A — CLI Simulator

```bash
python main.py
```

You'll be prompted to choose a file system, then interact via commands:

```
--- Cross-Platform File System Simulator ---
Choose file system type:
1. FAT32
2. EXT4
3. NTFS
> 2

Enter commands: create <name> <size_kb>, write <name> <data>, read <name>, delete <name>, list, info, exit
> create myfile 16
[EXT4] Created myfile (inode 1, 4 blocks)
> write myfile HelloWorld
[EXT4] Wrote to myfile (time 0.000012s)
> read myfile
b'HelloWorld'
> list
myfile
> info
EXT4: 4/2560 blocks used | Journal=True | Fragmentation=0.00% | Largest free run=2556 blocks
> exit
```

**Available CLI commands:**

| Command | Description |
|---|---|
| `create <name> <size_kb>` | Create a new file of given size |
| `write <name> <data>` | Write string data to a file |
| `read <name>` | Read and print file contents |
| `delete <name>` | Delete a file and free its blocks |
| `list` | List all files on the file system |
| `info` | Show disk usage, fragmentation, and FS details |
| `exit` | Close the file system and exit |

> **Note:** Each session creates a `virtual_disk_<fsname>.bin` file in the project root (e.g., `virtual_disk_ext4.bin`) representing a 10 MB virtual disk.

---

### Option B — Streamlit Dashboard

```bash
streamlit run app.py
```

Opens a web browser at `http://localhost:8501` with a clean single-page layout:

1. **Sidebar** — select file systems, file size, iterations, then click **▶ Run Benchmark**
2. **Metric cards** — at-a-glance avg write/read times per FS
3. **Charts** — grouped bar chart (read vs write) and scatter plot (write spread) side-by-side
4. **Results table** — expandable full data table
5. **Summary** — auto-generated conclusion identifying the best performer

---

## 🧪 Running Tests

```bash
pytest tests/ -v
```

Expected output:

```
tests/test_filesystem.py::... PASSED
...
====== X passed in 0.XXs ======
```

---

## 📐 How Each File System is Simulated

| Feature | FAT32 | EXT4 | NTFS |
|---------|-------|------|------|
| Allocation | FAT linked chain | Inode table + extent tree | Master File Table (MFT) |
| Contiguous alloc | No | Yes (tries first) | MFT extents (partial) |
| Journaling | No | Yes (simulated delay) | No |
| Fragmentation tracked | ✅ | ✅ | ✅ |
| Block size | 4 KB (default) | 4 KB (default) | 4 KB (default) |
| Max simulated disk | 10 MB (default) | 10 MB (default) | 10 MB (default) |

### FAT32 — Linked FAT Chain
Each file is stored as a chain of cluster entries in the File Allocation Table. The table maps cluster → next cluster, ending with an `EOF` marker. Fragmentation grows as files are deleted and re-created.

### EXT4 — Inodes + Journaling
Files are tracked via inode objects containing block pointers. The simulator attempts contiguous allocation first and falls back to scattered blocks. A simulated journal adds a small write overhead to model crash-recovery logging.

### NTFS — Master File Table (MFT)
Every file, directory, and metadata item is a record in the MFT. Each record stores extents (run-length encoded block ranges). Small files may be stored as resident data directly inside the MFT record.

---

## 🏗️ Extending the Project

To add a new file system:

1. Create `filesystems/yourfs.py` extending `BaseFileSystem`
2. Implement all 6 required methods:

```python
from filesystems.base_filesystem import BaseFileSystem

class YourFS(BaseFileSystem):
    def create_file(self, name: str, size_bytes: int): ...
    def write_file(self, name: str, data: bytes): ...
    def read_file(self, name: str) -> bytes: ...
    def delete_file(self, name: str): ...
    def list_files(self) -> list: ...
    def info(self) -> str: ...
```

3. Export it from `filesystems/__init__.py`:

```python
from .yourfs import YourFS
__all__ = ['FAT32', 'Ext4', 'NTFS', 'YourFS']
```

4. Add it to `FS_MAP` in `main.py`:

```python
FS_MAP = {
    '1': ('FAT32', FAT32),
    '2': ('EXT4', Ext4),
    '3': ('NTFS', NTFS),
    '4': ('YourFS', YourFS),   # ← add here
}
```

---

## 🔧 Troubleshooting

| Problem | Fix |
|---|---|
| `streamlit: command not found` | Run `pip install streamlit` or activate your venv first |
| `ModuleNotFoundError: No module named 'filesystems'` | Run `python main.py` from the **project root** (`OS/`), not from a subdirectory |
| `ModuleNotFoundError: No module named 'storage'` | Same as above — must be run from `OS/` |
| Virtual disk file grows large | Delete `virtual_disk_*.bin` files in the project root to reset |
| Streamlit page is blank | Hard-refresh the browser (`Ctrl+Shift+R`) or restart with `streamlit run app.py` |
| `pytest: command not found` | Run `pip install pytest` |
| Slow tests on Windows | Your antivirus may be scanning temp files; add the project folder to exclusions |
| Dashboard shows landing message | Click **▶ Run Benchmark** in the sidebar |

---

## 📚 Key Concepts to Study

| Topic | Relevance |
|---|---|
| FAT32 linked-chain allocation | Core of `fat32.py` |
| EXT4 inodes, extent tree, journaling | Core of `ext4.py` |
| NTFS MFT records and extents | Core of `ntfs.py` |
| Bitmap-based block allocation | `storage/virtual_disk.py` |
| Internal vs external fragmentation | `utils/fragmentation.py` |
| Abstract Base Classes in Python (`abc`) | `base_filesystem.py` pattern |
| `time.perf_counter()` for benchmarking | `utils/performance_metrics.py` |
| Streamlit `session_state`, sidebar layout | `app.py` dashboard |
| Plotly Express grouped bar / scatter charts | `app.py` graphs |

**Recommended reading:** *Operating System Concepts* by Silberschatz et al. (Dinosaur Book) — Chapters 13–14 (File System Interface & Implementation).

---

## 📄 License

Educational project — free to use, modify, and share.
