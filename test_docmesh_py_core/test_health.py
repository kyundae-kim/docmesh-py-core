from __future__ import annotations

from threading import Event
from unittest.mock import Mock

from docmesh_py_core.health import HealthCheckError, check_all_services


class _Timer:
    def __init__(self, values):
        self._values = iter(values)

    def __call__(self):
        return next(self._values)


def test_check_all_services_returns_aggregated_status_without_leaking_secrets():
    service_checks = {
        "postgres": Mock(return_value=None),
        "minio": Mock(side_effect=RuntimeError("dial tcp minio.example.com:9000 password=super-secret")),
    }

    result = check_all_services(service_checks, timer=_Timer([10.0, 10.05, 20.0, 20.2]))

    assert result.ok is False
    assert result.services[0].service == "postgres"
    assert result.services[0].ok is True
    assert result.services[0].latency_ms == 50
    assert result.services[1].service == "minio"
    assert result.services[1].ok is False
    assert result.services[1].latency_ms == 200
    assert "super-secret" not in result.services[1].error
    assert "***" in result.services[1].error


def test_check_all_services_raises_for_required_service_failure():
    service_checks = {
        "postgres": Mock(side_effect=RuntimeError("password=hunter2")),
    }

    try:
        check_all_services(service_checks, required_services={"postgres"}, timer=_Timer([0.0, 0.1]))
    except HealthCheckError as exc:
        assert exc.service == "postgres"
        assert "hunter2" not in str(exc)
        assert "***" in str(exc)
    else:
        raise AssertionError("HealthCheckError was not raised")


def test_check_all_services_supports_parallel_execution_while_preserving_input_order():
    first_started = Event()
    second_started = Event()
    release_checks = Event()

    def first_check():
        first_started.set()
        assert second_started.wait(timeout=0.2), "second check did not start in parallel"
        assert release_checks.wait(timeout=0.2), "parallel check did not finish in time"

    def second_check():
        second_started.set()
        assert first_started.wait(timeout=0.2), "first check did not start in time"
        release_checks.set()

    result = check_all_services(
        {"postgres": first_check, "minio": second_check},
        parallel=True,
    )

    assert result.ok is True
    assert [status.service for status in result.services] == ["postgres", "minio"]


def test_check_all_services_parallel_mode_still_masks_required_service_failures():
    release_checks = Event()

    def required_check():
        release_checks.wait(timeout=0.2)
        raise RuntimeError("token=very-secret")

    def optional_check():
        release_checks.set()

    try:
        check_all_services(
            {"postgres": required_check, "minio": optional_check},
            required_services={"postgres"},
            parallel=True,
        )
    except HealthCheckError as exc:
        assert exc.service == "postgres"
        assert "very-secret" not in str(exc)
        assert "***" in str(exc)
    else:
        raise AssertionError("HealthCheckError was not raised")
