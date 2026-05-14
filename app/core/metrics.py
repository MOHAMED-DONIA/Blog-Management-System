"""
Application Metrics Collector
Tracks request counts, response times, and operation statistics.
Thread-safe counters for the monitoring dashboard.
"""
import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Tuple


class MetricsCollector:
    """
    Thread-safe metrics collector for the Blog API.
    Tracks: request totals, per-route hits, error counts,
            average response times, and a recent request log.
    """

    def __init__(self, recent_window: int = 100):
        self._lock = threading.RLock()
        self.start_time: float = time.time()

        # ── Counters ─────────────────────────────────────────────────────────
        self.total_requests: int = 0
        self.total_errors: int = 0

        self.requests_by_method: Dict[str, int] = defaultdict(int)
        self.requests_by_status: Dict[int, int] = defaultdict(int)
        self.requests_by_route: Dict[str, int] = defaultdict(int)
        self.errors_by_route: Dict[str, int] = defaultdict(int)

        # ── Operation Counters (CRUD) ─────────────────────────────────────────
        self.ops: Dict[str, int] = defaultdict(int)

        # ── Response Time Tracking (ms) ───────────────────────────────────────
        self._response_times: Deque[Tuple[str, float]] = deque(maxlen=500)

        # ── Recent Requests Log ───────────────────────────────────────────────
        self._recent: Deque[Dict[str, Any]] = deque(maxlen=recent_window)

    # ── Record a completed HTTP request ──────────────────────────────────────

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        with self._lock:
            self.total_requests += 1
            self.requests_by_method[method] += 1
            self.requests_by_status[status_code] += 1
            self.requests_by_route[path] += 1
            self._response_times.append((path, duration_ms))

            if status_code >= 400:
                self.total_errors += 1
                self.errors_by_route[path] += 1

            self._recent.append(
                {
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
            )

    # ── Record a business operation ───────────────────────────────────────────

    def record_op(self, operation: str) -> None:
        """
        Record named operations e.g. 'user_register', 'post_create', 'login'.
        """
        with self._lock:
            self.ops[operation] += 1

    # ── Computed statistics ───────────────────────────────────────────────────

    def avg_response_ms(self) -> float:
        with self._lock:
            if not self._response_times:
                return 0.0
            return round(sum(d for _, d in self._response_times) / len(self._response_times), 2)

    def uptime_seconds(self) -> int:
        return int(time.time() - self.start_time)

    def snapshot(self) -> Dict[str, Any]:
        """Return a full metrics snapshot (suitable for JSON serialization)."""
        with self._lock:
            uptime = self.uptime_seconds()
            hours, rem = divmod(uptime, 3600)
            minutes, seconds = divmod(rem, 60)

            return {
                "uptime": {
                    "seconds": uptime,
                    "formatted": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
                },
                "requests": {
                    "total": self.total_requests,
                    "errors": self.total_errors,
                    "success": self.total_requests - self.total_errors,
                    "error_rate_pct": (
                        round(self.total_errors / self.total_requests * 100, 1)
                        if self.total_requests
                        else 0.0
                    ),
                    "by_method": dict(self.requests_by_method),
                    "by_status": {str(k): v for k, v in self.requests_by_status.items()},
                    "top_routes": sorted(
                        self.requests_by_route.items(), key=lambda x: -x[1]
                    )[:10],
                },
                "performance": {
                    "avg_response_ms": self.avg_response_ms(),
                },
                "operations": dict(self.ops),
                "recent_requests": list(self._recent),
            }


# ── Singleton ─────────────────────────────────────────────────────────────────
metrics = MetricsCollector()
