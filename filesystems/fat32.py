"""
Simple FAT32-like implementation.
This is a toy model: it stores a FAT table in memory and writes file blocks to the virtual disk.
"""
from .base_filesystem import BaseFileSystem
from collections import namedtuple
import math
from utils.performance_metrics import Perf
from utils.fragmentation import fragmentation_report

FileEntry = namedtuple('FileEntry', ['name', 'size', 'blocks'])

class FAT32(BaseFileSystem):
    def __init__(self, disk):
        super().__init__(disk)
        self.fat = [-1] * disk.num_blocks  # -1 = free, -2 = EOF, otherwise next block index
        self.files = {}
        self.perf = Perf()

    def _blocks_needed(self, size_bytes):
        return math.ceil(size_bytes / self.disk.block_size)

    def create_file(self, name, size_bytes):
        if name in self.files:
            raise RuntimeError('file exists')
        blocks = self.disk.allocate_blocks(self._blocks_needed(size_bytes), contiguous=False)
        # link them in FAT
        for i in range(len(blocks)-1):
            self.fat[blocks[i]] = blocks[i+1]
        self.fat[blocks[-1]] = -2
        self.files[name] = FileEntry(name, size_bytes, blocks)
        print(f'[FAT32] Created {name} size={size_bytes} bytes blocks={len(blocks)}')

    def write_file(self, name, data):
        if name not in self.files:
            raise RuntimeError('no such file')
        entry = self.files[name]
        self.perf.start()
        # write chunk by chunk to allocated blocks
        remaining = data[:entry.size]
        for i, bidx in enumerate(entry.blocks):
            chunk = remaining[:self.disk.block_size]
            self.disk.write_block(bidx, chunk)
            remaining = remaining[self.disk.block_size:]
        self.perf.stop(len(data))
        print(f'[FAT32] Wrote {len(data)} bytes to {name} (time {self.perf.last_duration:.6f}s)')

    def read_file(self, name):
        if name not in self.files:
            raise RuntimeError('no such file')
        entry = self.files[name]
        out = bytearray()
        for b in entry.blocks:
            out += self.disk.read_block(b)
        return out[:entry.size]

    def delete_file(self, name):
        if name not in self.files:
            raise RuntimeError('no such file')
        entry = self.files.pop(name)
        for b in entry.blocks:
            self.fat[b] = -1
        self.disk.free_blocks(entry.blocks)
        print(f'[FAT32] Deleted {name}')

    def list_files(self):
        return [f'{e.name} ({e.size} bytes, blocks={len(e.blocks)})' for e in self.files.values()]

    def info(self):
        report = fragmentation_report(self.disk.bitmap)
        return (
            f"FAT32: {report['used_blocks']}/{report['total_blocks']} blocks used"
            f" | Files: {len(self.files)}"
            f" | Fragmentation={report['fragmentation_level']:.2%}"
            f" | Largest free run={report['largest_free_run']} blocks"
        )