"""
Unit tests for the Cross-Platform File System Simulator.
Run with:  pytest tests/ -v
"""
import sys
import os
import pytest

# Make sure project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from storage.virtual_disk import VirtualDisk
from filesystems.fat32 import FAT32
from filesystems.ext4 import Ext4
from filesystems.ntfs import NTFS
from utils.fragmentation import fragmentation_level, largest_free_run, fragmentation_report
from utils.performance_metrics import Perf, timeit


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_disk(tmp_path):
    """Create a small (1 MB) VirtualDisk backed by a temp file."""
    disk_path = str(tmp_path / "test_disk.bin")
    return VirtualDisk(disk_path, size_bytes=1 * 1024 * 1024, block_size=4096)


@pytest.fixture
def fat32_fs(tmp_disk):
    return FAT32(tmp_disk)


@pytest.fixture
def ext4_fs(tmp_disk):
    return Ext4(tmp_disk, journal_enabled=False)  # disable sleep for speed


@pytest.fixture
def ntfs_fs(tmp_disk):
    return NTFS(tmp_disk)


# ── VirtualDisk tests ─────────────────────────────────────────────────────────

class TestVirtualDisk:
    def test_block_count(self, tmp_disk):
        assert tmp_disk.num_blocks == (1 * 1024 * 1024) // 4096

    def test_write_and_read_block(self, tmp_disk):
        data = b"Hello, World!"
        tmp_disk.bitmap[0] = 1  # mark as used manually for raw test
        tmp_disk.write_block(0, data)
        result = tmp_disk.read_block(0)
        assert result[:len(data)] == data

    def test_allocate_contiguous(self, tmp_disk):
        blocks = tmp_disk.allocate_blocks(3, contiguous=True)
        assert len(blocks) == 3
        assert blocks == list(range(blocks[0], blocks[0] + 3))

    def test_allocate_non_contiguous(self, tmp_disk):
        blocks = tmp_disk.allocate_blocks(5, contiguous=False)
        assert len(blocks) == 5

    def test_free_blocks(self, tmp_disk):
        blocks = tmp_disk.allocate_blocks(4, contiguous=False)
        tmp_disk.free_blocks(blocks)
        for b in blocks:
            assert tmp_disk.bitmap[b] == 0

    def test_out_of_range_read(self, tmp_disk):
        with pytest.raises(IndexError):
            tmp_disk.read_block(tmp_disk.num_blocks + 1)

    def test_data_too_large_write(self, tmp_disk):
        with pytest.raises(ValueError):
            tmp_disk.write_block(0, b"x" * (tmp_disk.block_size + 1))


# ── FAT32 tests ───────────────────────────────────────────────────────────────

class TestFAT32:
    def test_create_file(self, fat32_fs):
        fat32_fs.create_file("readme.txt", 4096)
        assert "readme.txt" in fat32_fs.files

    def test_create_duplicate_raises(self, fat32_fs):
        fat32_fs.create_file("dup.txt", 1024)
        with pytest.raises(RuntimeError, match="file exists"):
            fat32_fs.create_file("dup.txt", 1024)

    def test_write_and_read(self, fat32_fs):
        fat32_fs.create_file("data.bin", 4096)
        payload = b"FAT32 test data"
        fat32_fs.write_file("data.bin", payload)
        result = fat32_fs.read_file("data.bin")
        assert result[:len(payload)] == payload

    def test_delete_file(self, fat32_fs):
        fat32_fs.create_file("del.txt", 4096)
        fat32_fs.delete_file("del.txt")
        assert "del.txt" not in fat32_fs.files

    def test_delete_nonexistent_raises(self, fat32_fs):
        with pytest.raises(RuntimeError, match="no such file"):
            fat32_fs.delete_file("ghost.txt")

    def test_list_files(self, fat32_fs):
        fat32_fs.create_file("a.txt", 1024)
        fat32_fs.create_file("b.txt", 2048)
        listing = fat32_fs.list_files()
        assert any("a.txt" in entry for entry in listing)
        assert any("b.txt" in entry for entry in listing)

    def test_info_contains_fragmentation(self, fat32_fs):
        fat32_fs.create_file("f.txt", 4096)
        info = fat32_fs.info()
        assert "FAT32" in info
        assert "Fragmentation" in info


# ── EXT4 tests ────────────────────────────────────────────────────────────────

class TestExt4:
    def test_create_file_assigns_inode(self, ext4_fs):
        ext4_fs.create_file("kernel.log", 4096)
        inode = ext4_fs.inodes["kernel.log"]
        assert inode.inode_no == 1

    def test_inode_increments(self, ext4_fs):
        ext4_fs.create_file("a.txt", 4096)
        ext4_fs.create_file("b.txt", 4096)
        assert ext4_fs.inodes["a.txt"].inode_no == 1
        assert ext4_fs.inodes["b.txt"].inode_no == 2

    def test_write_and_read(self, ext4_fs):
        ext4_fs.create_file("hello.txt", 4096)
        data = b"EXT4 inode data"
        ext4_fs.write_file("hello.txt", data)
        result = ext4_fs.read_file("hello.txt")
        assert result[:len(data)] == data

    def test_delete_frees_inode(self, ext4_fs):
        ext4_fs.create_file("temp.txt", 4096)
        ext4_fs.delete_file("temp.txt")
        assert "temp.txt" not in ext4_fs.inodes

    def test_info_contains_journal_status(self, ext4_fs):
        info = ext4_fs.info()
        assert "EXT4" in info
        assert "Journal" in info
        assert "Fragmentation" in info

    def test_read_nonexistent_raises(self, ext4_fs):
        with pytest.raises(RuntimeError, match="No such file"):
            ext4_fs.read_file("missing.txt")


# ── NTFS tests ────────────────────────────────────────────────────────────────

class TestNTFS:
    def test_create_file_assigns_mft_id(self, ntfs_fs):
        ntfs_fs.create_file("report.docx", 8192)
        entry = ntfs_fs.mft["report.docx"]
        assert entry.mft_id == 1

    def test_write_and_read(self, ntfs_fs):
        ntfs_fs.create_file("ntfs_test.bin", 4096)
        payload = b"NTFS MFT data"
        ntfs_fs.write_file("ntfs_test.bin", payload)
        result = ntfs_fs.read_file("ntfs_test.bin")
        assert result[:len(payload)] == payload

    def test_delete_removes_mft_entry(self, ntfs_fs):
        ntfs_fs.create_file("x.bin", 4096)
        ntfs_fs.delete_file("x.bin")
        assert "x.bin" not in ntfs_fs.mft

    def test_info_contains_fragmentation(self, ntfs_fs):
        ntfs_fs.create_file("f.txt", 4096)
        info = ntfs_fs.info()
        assert "NTFS" in info
        assert "Fragmentation" in info

    def test_create_duplicate_raises(self, ntfs_fs):
        ntfs_fs.create_file("dup.bin", 4096)
        with pytest.raises(RuntimeError, match="File already exists"):
            ntfs_fs.create_file("dup.bin", 4096)


# ── Fragmentation utils tests ─────────────────────────────────────────────────

class TestFragmentation:
    def test_no_free_blocks(self):
        assert fragmentation_level([1, 1, 1]) == 0.0

    def test_all_free_blocks(self):
        # Single contiguous free run → level = 1/3 ≈ 0.333
        assert fragmentation_level([0, 0, 0]) == pytest.approx(1 / 3)

    def test_fragmented_bitmap(self):
        # [1,0,1,0,1] → 2 free runs, 2 free blocks → level = 1.0
        assert fragmentation_level([1, 0, 1, 0, 1]) == pytest.approx(1.0)

    def test_largest_free_run(self):
        assert largest_free_run([1, 0, 0, 0, 1, 0]) == 3

    def test_fragmentation_report_keys(self):
        report = fragmentation_report([1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1])
        assert set(report.keys()) == {
            'total_blocks', 'free_blocks', 'used_blocks',
            'free_runs', 'largest_free_run', 'fragmentation_level'
        }

    def test_fragmentation_report_values(self):
        bitmap = [1, 0, 0, 1, 0]  # 3 free blocks in 2 runs, largest run = 2
        report = fragmentation_report(bitmap)
        assert report['total_blocks'] == 5
        assert report['free_blocks'] == 3
        assert report['used_blocks'] == 2
        assert report['free_runs'] == 2
        assert report['largest_free_run'] == 2


# ── Perf timer tests ──────────────────────────────────────────────────────────

class TestPerf:
    def test_duration_positive(self):
        p = Perf()
        p.start()
        _ = sum(range(10000))
        p.stop()
        assert p.last_duration > 0

    def test_throughput_calculated(self):
        p = Perf()
        p.start()
        _ = sum(range(10000))
        p.stop(bytes_transferred=1024)
        assert p.throughput is not None
        assert p.throughput > 0

    def test_context_manager(self):
        with Perf() as p:
            _ = sum(range(10000))
        assert p.last_duration > 0

    def test_timeit_decorator(self):
        @timeit
        def add(a, b):
            return a + b

        result, duration = add(3, 4)
        assert result == 7
        assert duration >= 0

    def test_reset(self):
        p = Perf()
        p.start()
        p.stop(100)
        p.reset()
        assert p.last_duration == 0.0
        assert p.throughput is None
