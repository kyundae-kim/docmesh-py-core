from __future__ import annotations

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
