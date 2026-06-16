from __future__ import annotations

from collections.abc import Callable, Mapping, Set
from concurrent.futures import Future, ThreadPoolExecutor
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


def _run_service_check(
    service_name: str,
    check: CheckFn,
    *,
    timer: Callable[[], float],
) -> tuple[ServiceHealthStatus, Exception | None]:
    start = timer()
    try:
        check()
    except Exception as exc:
        latency_ms = int(round((timer() - start) * 1000))
        error = mask_sensitive_value(str(exc))
        return (
            ServiceHealthStatus(service=service_name, ok=False, latency_ms=latency_ms, error=error),
            exc,
        )

    latency_ms = int(round((timer() - start) * 1000))
    return ServiceHealthStatus(service=service_name, ok=True, latency_ms=latency_ms), None


def check_all_services(
    service_checks: Mapping[str, CheckFn],
    *,
    required_services: Set[str] | None = None,
    timer: Callable[[], float] = time.perf_counter,
    parallel: bool = False,
) -> HealthCheckResult:
    required_services = required_services or set()
    if not parallel:
        statuses: list[ServiceHealthStatus] = []

        for service_name, check in service_checks.items():
            status, exc = _run_service_check(service_name, check, timer=timer)
            statuses.append(status)
            if exc is not None and service_name in required_services:
                raise HealthCheckError(service_name, status.error or "unknown error") from exc

        return HealthCheckResult(ok=all(status.ok for status in statuses), services=statuses)

    if not service_checks:
        return HealthCheckResult(ok=True, services=[])

    futures: list[tuple[str, Future[tuple[ServiceHealthStatus, Exception | None]]]] = []

    with ThreadPoolExecutor(max_workers=len(service_checks)) as executor:
        for service_name, check in service_checks.items():
            futures.append((service_name, executor.submit(_run_service_check, service_name, check, timer=timer)))

    statuses: list[ServiceHealthStatus] = []
    failure_causes: dict[str, Exception] = {}

    for service_name, future in futures:
        status, exc = future.result()
        statuses.append(status)
        if exc is not None:
            failure_causes[service_name] = exc

    for status in statuses:
        if not status.ok and status.service in required_services:
            raise HealthCheckError(status.service, status.error or "unknown error") from failure_causes.get(status.service)

    return HealthCheckResult(ok=all(status.ok for status in statuses), services=statuses)
