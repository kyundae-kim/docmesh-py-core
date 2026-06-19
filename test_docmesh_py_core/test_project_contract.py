from __future__ import annotations

from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_pytest_markers_are_registered_for_documented_test_slices():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    markers = set(pyproject["tool"]["pytest"]["ini_options"]["markers"])

    expected_markers = {
        "unit: mark test as unit test (no external network dependencies)",
        "integration: mark test as integration test (requires external services)",
        "security: mark test as security-focused regression coverage",
        "keycloak: mark test as Keycloak-specific coverage",
        "health: mark test as service health-check coverage",
    }

    assert expected_markers.issubset(markers)


def test_test_guide_documents_uv_run_pytest_contract():
    test_guide = (PROJECT_ROOT / "docs" / "test.md").read_text(encoding="utf-8")

    assert 'uv run pytest -q test_docmesh_py_core' in test_guide
    assert 'uv run pytest -q -m "not integration"' in test_guide
    assert 'DOCMESH_ENV=integration uv run pytest -q -m integration' in test_guide


def test_test_guide_example_structure_has_dedicated_security_and_provisioning_files():
    security_test = PROJECT_ROOT / "test_docmesh_py_core" / "test_security.py"
    provisioning_test = PROJECT_ROOT / "test_docmesh_py_core" / "test_keycloak_provisioning.py"

    assert security_test.exists()
    assert provisioning_test.exists()


def test_keycloak_related_tests_are_split_by_concern():
    keycloak_test = (PROJECT_ROOT / "test_docmesh_py_core" / "test_keycloak.py").read_text(encoding="utf-8")
    security_test = (PROJECT_ROOT / "test_docmesh_py_core" / "test_security.py").read_text(encoding="utf-8")
    provisioning_test = (PROJECT_ROOT / "test_docmesh_py_core" / "test_keycloak_provisioning.py").read_text(encoding="utf-8")

    assert "KeycloakProvisioner" not in keycloak_test
    assert "mask" in security_test.lower()
    assert "KeycloakProvisioner" in provisioning_test


def test_unit_test_conftest_centralizes_environment_isolation():
    conftest = (PROJECT_ROOT / "test_docmesh_py_core" / "conftest.py").read_text(encoding="utf-8")

    assert "DOCMESH_ENV_PREFIXES" in conftest
    assert "clear_docmesh_environment_for_unit_tests" in conftest
    assert "request.node.get_closest_marker(\"integration\")" in conftest
    assert "monkeypatch.delenv(env_key, raising=False)" in conftest


def test_integration_tests_use_shared_helpers_from_conftest():
    integration_tests = (PROJECT_ROOT / "test_docmesh_py_core" / "test_integration_services.py").read_text(encoding="utf-8")

    assert "from test_docmesh_py_core.conftest import" in integration_tests
    assert "integration_env" in integration_tests
    assert "require_integration_environment" in integration_tests
    assert "service_env" in integration_tests
