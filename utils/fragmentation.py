"""
Utilities to measure simple fragmentation metrics for the virtual disk bitmap.

Functions:
- fragmentation_level(bitmap): naive fragmentation metric (free_runs / total_free_blocks)
- fragmentation_report(bitmap): returns a dict with multiple fragmentation stats
- largest_free_run(bitmap): length of the largest contiguous free block run
"""

from typing import List, Dict


def fragmentation_level(bitmap: List[int]) -> float:
    """
    Naive fragmentation metric: number_of_free_runs / total_free_blocks
    Lower is better (0 = perfectly contiguous free space).
    Returns 0.0 if there are no free blocks.
    """
    free_runs = 0
    in_run = False
    total_free = 0
    for b in bitmap:
        if b == 0:
            total_free += 1
            if not in_run:
                in_run = True
                free_runs += 1
        else:
            in_run = False
    if total_free == 0:
        return 0.0
    return free_runs / total_free


def largest_free_run(bitmap: List[int]) -> int:
    """Return the size (in blocks) of the largest contiguous free-run."""
    max_run = 0
    cur = 0
    for b in bitmap:
        if b == 0:
            cur += 1
            if cur > max_run:
                max_run = cur
        else:
            cur = 0
    return max_run


def fragmentation_report(bitmap: List[int]) -> Dict[str, float]:
    """
    Return a dictionary with several fragmentation-related statistics:
    {
        'total_blocks': int,
        'free_blocks': int,
        'used_blocks': int,
        'free_runs': int,
        'largest_free_run': int,
        'fragmentation_level': float  # free_runs / free_blocks
    }
    """
    total = len(bitmap)
    free_blocks = 0
    free_runs = 0
    in_run = False
    for b in bitmap:
        if b == 0:
            free_blocks += 1
            if not in_run:
                in_run = True
                free_runs += 1
        else:
            in_run = False

    largest_run = largest_free_run(bitmap)
    frag_level = fragmentation_level(bitmap)

    return {
        'total_blocks': total,
        'free_blocks': free_blocks,
        'used_blocks': total - free_blocks,
        'free_runs': free_runs,
        'largest_free_run': largest_run,
        'fragmentation_level': frag_level,
    }


if __name__ == '__main__':
    # quick demo when run directly
    sample = [1, 1, 0, 0, 1, 0, 1, 0, 0, 0, 1]
    print(fragmentation_report(sample))
