"""Shared monotonic time budget for forum work and bounded cleanup."""
import math
import time
from .http_source import FetchError


class Budget:
    def __init__(self, total_seconds: float, *, clock=time.monotonic):
        if isinstance(total_seconds, bool) or not isinstance(total_seconds, (int,float)) or not math.isfinite(total_seconds) or not 1 <= total_seconds <= 1800:
            raise ValueError('total_timeout 需要 1–1800 秒')
        self.clock = clock
        self.deadline = clock()+total_seconds
        self.cleanup_deadline = None

    def remaining(self) -> float:
        return max(0.0, self.deadline-self.clock()) if self.cleanup_deadline is None else 0.0

    def timeout_for(self, per_call: float) -> float:
        remaining = self.remaining()
        if remaining <= 0: raise FetchError('budget_exhausted', '扫描总时限已到')
        return min(per_call, remaining)

    def stop(self) -> None:
        if self.cleanup_deadline is None: self.cleanup_deadline = self.clock()+5

    def cleanup_timeout(self) -> float:
        if self.cleanup_deadline is None and self.remaining() > 0:
            return min(5, self.remaining())
        if self.cleanup_deadline is None: self.stop()
        left = self.cleanup_deadline-self.clock()
        if left <= 0: raise FetchError('budget_exhausted', '清理时限已到')
        return left
