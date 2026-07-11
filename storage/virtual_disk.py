import os
import math

class VirtualDisk:
    def __init__(self, path, size_bytes=10*1024*1024, block_size=4096):
        self.path = path
        self.size = size_bytes
        self.block_size = block_size
        self.num_blocks = math.ceil(self.size / self.block_size)
        self._ensure_disk()
        # simple bitmap for allocations (0=free,1=used)
        self.bitmap = [0] * self.num_blocks

    def _ensure_disk(self):
        if not os.path.exists(self.path):
            with open(self.path, 'wb') as f:
                f.truncate(self.size)

    def read_block(self, block_index):
        if block_index < 0 or block_index >= self.num_blocks:
            raise IndexError('block out of range')
        with open(self.path, 'rb') as f:
            f.seek(block_index * self.block_size)
            return f.read(self.block_size)

    def write_block(self, block_index, data):
        if block_index < 0 or block_index >= self.num_blocks:
            raise IndexError('block out of range')
        if len(data) > self.block_size:
            raise ValueError('data larger than block')
        with open(self.path, 'r+b') as f:
            f.seek(block_index * self.block_size)
            f.write(data.ljust(self.block_size, b'\x00'))

    def allocate_blocks(self, count, contiguous=False):
        """Allocate blocks. If contiguous True, try to find contiguous run."""
        if contiguous:
            run = 0
            start = -1
            for i, b in enumerate(self.bitmap):
                if b == 0:
                    run += 1
                    if start == -1:
                        start = i
                    if run == count:
                        for j in range(start, start+count):
                            self.bitmap[j] = 1
                        return list(range(start, start+count))
                else:
                    run = 0
                    start = -1
            raise RuntimeError('No contiguous space')
        else:
            res = []
            for i, b in enumerate(self.bitmap):
                if b == 0:
                    self.bitmap[i] = 1
                    res.append(i)
                    if len(res) == count:
                        return res
            raise RuntimeError('Not enough space')

    def free_blocks(self, block_indices):
        for i in block_indices:
            self.bitmap[i] = 0

    def close(self):
        pass