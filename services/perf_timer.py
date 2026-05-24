import time
from typing import Optional


class PerfTimer:
    def __init__(self, name: str = ""):
        self.name = name
        self.start_time: Optional[float] = None
        self.elapsed: float = 0.0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        if self.start_time is not None:
            self.elapsed = time.time() - self.start_time

    def get_elapsed(self) -> float:
        if self.start_time is not None:
            return time.time() - self.start_time
        return self.elapsed
