from dataclasses import dataclass


@dataclass
class MetricBucket:
    total: int = 0
    cached: int = 0
    errors: int = 0
    latency_total_ms: float = 0.0

    def record(self, duration_ms: float, cached: bool, error: bool) -> None:
        self.total += 1
        if cached:
            self.cached += 1
        if error:
            self.errors += 1
        self.latency_total_ms += duration_ms

    def snapshot(self) -> dict[str, float | int]:
        avg = self.latency_total_ms / self.total if self.total else 0.0
        return {
            "total": self.total,
            "cached": self.cached,
            "errors": self.errors,
            "avg_latency_ms": round(avg, 2),
        }


class WishlistMetrics:
    def __init__(self) -> None:
        self.items = MetricBucket()
        self.lists = MetricBucket()

    def record_item(self, duration_ms: float, cached: bool, error: bool) -> None:
        self.items.record(duration_ms, cached, error)

    def record_list(self, duration_ms: float, cached: bool, error: bool) -> None:
        self.lists.record(duration_ms, cached, error)

    def snapshot(self) -> dict[str, dict[str, float | int]]:
        return {
            "wishlist_item": self.items.snapshot(),
            "wishlist_list": self.lists.snapshot(),
        }


wishlist_metrics = WishlistMetrics()
