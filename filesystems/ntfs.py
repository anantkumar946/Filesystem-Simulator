"""
Simplified NTFS-like simulator using Master File Table (MFT) concept.
"""
from .base_filesystem import BaseFileSystem
from collections import namedtuple
import math
from utils.performance_metrics import Perf
from utils.fragmentation import fragmentation_report


MFTEntry = namedtuple('MFTEntry', ['name', 'size', 'blocks', 'mft_id'])


class NTFS(BaseFileSystem):
    def __init__(self, disk):
        super().__init__(disk)
        self.mft = {}
        self.next_id = 1
        self.perf = Perf()

    def _blocks_needed(self, size_bytes):
        return math.ceil(size_bytes / self.disk.block_size)

    def create_file(self, name, size_bytes):
        if name in self.mft:
            raise RuntimeError('File already exists')

        blocks_needed = self._blocks_needed(size_bytes)
        blocks = self.disk.allocate_blocks(blocks_needed, contiguous=False)
        entry = MFTEntry(name, size_bytes, blocks, self.next_id)
        self.next_id += 1
        self.mft[name] = entry

        print(f'[NTFS] Created {name} (MFT ID {entry.mft_id}, {len(blocks)} blocks)')

    def write_file(self, name, data):
        if name not in self.mft:
            raise RuntimeError('No such file')

        entry = self.mft[name]
        self.perf.start()

        for bidx in entry.blocks:
            chunk = data[:self.disk.block_size]
            self.disk.write_block(bidx, chunk)
            data = data[self.disk.block_size:]

        self.perf.stop(len(data))
        print(f'[NTFS] Wrote to {name} (time {self.perf.last_duration:.6f}s)')

    def read_file(self, name):
        if name not in self.mft:
            raise RuntimeError('No such file')

        entry = self.mft[name]
        out = bytearray()

        for b in entry.blocks:
            out += self.disk.read_block(b)

        return out[:entry.size]

    def delete_file(self, name):
        if name not in self.mft:
            raise RuntimeError('No such file')

        entry = self.mft.pop(name)
        self.disk.free_blocks(entry.blocks)
        print(f'[NTFS] Deleted {name} (MFT ID {entry.mft_id})')

    def list_files(self):
        return [
            f'{entry.name} (MFT={entry.mft_id}, size={entry.size} bytes)'
            for entry in self.mft.values()
        ]

    def info(self):
        report = fragmentation_report(self.disk.bitmap)
        return (
            f"NTFS: {report['used_blocks']}/{report['total_blocks']} blocks used"
            f" | Files: {len(self.mft)}"
            f" | Fragmentation={report['fragmentation_level']:.2%}"
            f" | Largest free run={report['largest_free_run']} blocks"
        )
