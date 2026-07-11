"""
Simple performance measurement utilities (micro-benchmarking).

Provides:
- Perf class with start/stop, context manager support, throughput calculation
- timeit decorator helper
"""

import time
from contextlib import ContextDecorator
from typing import Optional, Callable, Any


class Perf(ContextDecorator):
    """
    Performance timer. Usage:

    p = Perf()
    p.start()
    ... do work ...
    p.stop(bytes_transferred=1024)
    print(p.last_duration, p.throughput)

    Or as a context manager:

    with Perf() as p:
        ... work ...
    # p.last_duration is available after the block
    """

    def __init__(self):
        self.start_ts: Optional[float] = None
        self.last_duration: float = 0.0
        self.last_bytes: int = 0
        self.throughput: Optional[float] = None  # bytes/sec

    def start(self):
        self.start_ts = time.perf_counter()

    def stop(self, bytes_transferred: int = 0):
        if self.start_ts is None:
            self.last_duration = 0.0
            self.throughput = None
            return
        self.last_duration = time.perf_counter() - self.start_ts
        self.last_bytes = bytes_transferred
        if self.last_duration > 0 and bytes_transferred:
            self.throughput = bytes_transferred / self.last_duration
        else:
            self.throughput = None
        self.start_ts = None

    # Context manager support
    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        # do not compute throughput automatically unless bytes were set manually
        if self.start_ts is not None:
            self.stop(self.last_bytes)
        return False  # do not suppress exceptions

    def reset(self):
        self.start_ts = None
        self.last_duration = 0.0
        self.last_bytes = 0
        self.throughput = None


def timeit(func: Callable) -> Callable:
    """
    Decorator to measure execution time of a function.
    The wrapped function will return a tuple: (result, duration_seconds)
    """

    def wrapper(*args, **kwargs) -> Any:
        t0 = time.perf_counter()
        res = func(*args, **kwargs)
        dt = time.perf_counter() - t0
        return res, dt

    wrapper.__name__ = getattr(func, "__name__", "wrapped")
    wrapper.__doc__ = func.__doc__
    return wrapper


if __name__ == '__main__':
    # quick demo
    with Perf() as p:
        s = 0
        for i in range(1000000):
            s += i
    print('Duration:', p.last_duration)
