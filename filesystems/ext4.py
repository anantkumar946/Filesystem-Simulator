"""
Simplified EXT4-like simulator with inodes and journaling simulation.
"""
from .base_filesystem import BaseFileSystem
from collections import namedtuple
import math
import time
from utils.performance_metrics import Perf
from utils.fragmentation import fragmentation_report

Inode = namedtuple('Inode', ['name', 'size', 'blocks', 'inode_no'])


class Ext4(BaseFileSystem):
    def __init__(self, disk, journal_enabled=True):
        super().__init__(disk)
        self.inodes = {}
        self.next_inode = 1
        self.perf = Perf()
        self.journal_enabled = journal_enabled

    def _blocks_needed(self, size_bytes):
        return math.ceil(size_bytes / self.disk.block_size)

    def create_file(self, name, size_bytes):
        if name in self.inodes:
            raise RuntimeError('File already exists')
        blocks_needed = self._blocks_needed(size_bytes)
        try:
            blocks = self.disk.allocate_blocks(blocks_needed, contiguous=True)
        except RuntimeError:
            blocks = self.disk.allocate_blocks(blocks_needed, contiguous=False)

        inode = Inode(name, size_bytes, blocks, self.next_inode)
        self.next_inode += 1
        self.inodes[name] = inode

        if self.journal_enabled:
            time.sleep(0.0001 * len(blocks))  # simulate journal overhead

        print(f'[EXT4] Created {name} (inode {inode.inode_no}, {len(blocks)} blocks)')

    def write_file(self, name, data):
        if name not in self.inodes:
            raise RuntimeError('No such file')
        inode = self.inodes[name]
        self.perf.start()
        for bidx in inode.blocks:
            chunk = data[:self.disk.block_size]
            self.disk.write_block(bidx, chunk)
            data = data[self.disk.block_size:]
        self.perf.stop(len(data))
        print(f'[EXT4] Wrote to {name} (time {self.perf.last_duration:.6f}s)')

    def read_file(self, name):
        if name not in self.inodes:
            raise RuntimeError('No such file')
        inode = self.inodes[name]
        out = bytearray()
        for b in inode.blocks:
            out += self.disk.read_block(b)
        return out[:inode.size]

    def delete_file(self, name):
        if name not in self.inodes:
            raise RuntimeError('No such file')
        inode = self.inodes.pop(name)
        self.disk.free_blocks(inode.blocks)
        print(f'[EXT4] Deleted {name} (inode {inode.inode_no})')

    def list_files(self):
        return [
            f'{inode.name} (inode={inode.inode_no}, size={inode.size} bytes)'
            for inode in self.inodes.values()
        ]

    def info(self):
        report = fragmentation_report(self.disk.bitmap)
        return (
            f"EXT4: {report['used_blocks']}/{report['total_blocks']} blocks used"
            f" | Journal={self.journal_enabled}"
            f" | Fragmentation={report['fragmentation_level']:.2%}"
            f" | Largest free run={report['largest_free_run']} blocks"
        )
