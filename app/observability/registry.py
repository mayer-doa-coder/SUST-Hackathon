from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import RLock
from time import time

from app.config import get_settings


@dataclass
class RequestTrace:
    correlation_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    timestamp: float


class ObservabilityRegistry:
    def __init__(self) -> None:
        self._lock = RLock()
        self._request_counts: dict[tuple[str, str, int], int] = defaultdict(int)
        self._request_duration_ms: dict[tuple[str, str], list[float]] = defaultdict(list)
        self._recent_traces: deque[RequestTrace] = deque()

    def record_request(
        self,
        correlation_id: str,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        settings = get_settings()
        with self._lock:
            self._request_counts[(method, path, status_code)] += 1
            self._request_duration_ms[(method, path)].append(duration_ms)
            self._recent_traces.append(
                RequestTrace(
                    correlation_id=correlation_id,
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    timestamp=time(),
                )
            )
            while len(self._recent_traces) > settings.observability_recent_trace_limit:
                self._recent_traces.popleft()

    def metrics_text(self) -> str:
        lines = [
            "# HELP queuestorm_http_requests_total Total HTTP requests by method, path, and status.",
            "# TYPE queuestorm_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status_code), count in sorted(self._request_counts.items()):
                lines.append(
                    f'queuestorm_http_requests_total{{method="{method}",path="{path}",status="{status_code}"}} {count}'
                )
            lines.extend(
                [
                    "# HELP queuestorm_http_request_duration_ms_avg Average HTTP request duration in milliseconds.",
                    "# TYPE queuestorm_http_request_duration_ms_avg gauge",
                ]
            )
            for (method, path), values in sorted(self._request_duration_ms.items()):
                average = sum(values) / len(values) if values else 0.0
                lines.append(f'queuestorm_http_request_duration_ms_avg{{method="{method}",path="{path}"}} {average:.3f}')
        return "\n".join(lines) + "\n"

    def recent_traces(self) -> list[RequestTrace]:
        with self._lock:
            return list(self._recent_traces)

    def reset(self) -> None:
        with self._lock:
            self._request_counts.clear()
            self._request_duration_ms.clear()
            self._recent_traces.clear()


observability_registry = ObservabilityRegistry()
