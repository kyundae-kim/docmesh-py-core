from __future__ import annotations

from collections.abc import Callable, Mapping, Set
from dataclasses import dataclass
import time

from .security import mask_sensitive_value


@dataclass(frozen=True)
class ServiceHealthStatus:
    service: str
    ok: bool
    latency_ms: int
    error: str | None = None


@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool
    services: list[ServiceHealthStatus]


class HealthCheckError(RuntimeError):
    def __init__(self, service: str, error: str):
        super().__init__(f"Required service health check failed for {service}: {error}")
        self.service = service
        self.error = error


CheckFn = Callable[[], object]


def check_all_services(
    service_checks: Mapping[str, CheckFn],
    *,
    required_services: Set[str] | None = None,
    timer: Callable[[], float] = time.perf_counter,
) -> HealthCheckResult:
    required_services = required_services or set()
    statuses: list[ServiceHealthStatus] = []

    for service_name, check in service_checks.items():
        start = timer()
        try:
            check()
        except Exception as exc:
            latency_ms = int(round((timer() - start) * 1000))
            error = mask_sensitive_value(str(exc))
            status = ServiceHealthStatus(service=service_name, ok=False, latency_ms=latency_ms, error=error)
            statuses.append(status)
            if service_name in required_services:
                raise HealthCheckError(service_name, error or "unknown error") from exc
        else:
            latency_ms = int(round((timer() - start) * 1000))
            statuses.append(ServiceHealthStatus(service=service_name, ok=True, latency_ms=latency_ms))

    return HealthCheckResult(ok=all(status.ok for status in statuses), services=statuses)
