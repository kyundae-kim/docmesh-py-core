from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from test_docmesh_py_core import conftest as test_conftest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


pytestmark = [pytest.mark.unit]


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
    assert "require_integration_environment" in integration_tests
    assert "docmesh_env_context" in integration_tests
    assert "KeycloakIntegrationConfig" in integration_tests
    assert "PostgresIntegrationConfig" in integration_tests
    assert "NatsIntegrationConfig" in integration_tests


def test_integration_test_module_documents_explicit_docmesh_env_gate():
    integration_tests = (PROJECT_ROOT / "test_docmesh_py_core" / "test_integration_services.py").read_text(encoding="utf-8")
    conftest = (PROJECT_ROOT / "test_docmesh_py_core" / "conftest.py").read_text(encoding="utf-8")

    assert 'pytestmark = [pytest.mark.integration]' in integration_tests
    assert 'INTEGRATION_ENV_NAME = "integration"' in conftest
    assert 'current_env != INTEGRATION_ENV_NAME' in conftest
    assert 'pytest.skip("Set DOCMESH_ENV=integration to run real-service integration tests")' in conftest


def test_common_integration_config_only_reads_dedicated_integration_file_before_process_env():
    conftest = (PROJECT_ROOT / "test_docmesh_py_core" / "conftest.py").read_text(encoding="utf-8")

    assert "parse_env_file(ROOT / 'env' / 'integration.env')" in conftest
    assert 'CommonIntegrationConfig()' in conftest
    assert 'ROOT / ".env"' not in conftest


def test_integration_common_config_returns_common_integration_settings_object(monkeypatch: pytest.MonkeyPatch):
    class FakeCommonIntegrationConfig:
        env = "integration"
        healthcheck_enabled = True

    monkeypatch.setattr(test_conftest, "CommonIntegrationConfig", FakeCommonIntegrationConfig)
    monkeypatch.setattr(test_conftest, "parse_env_file", lambda _: {})

    env = test_conftest.integration_common_config()

    assert isinstance(env, FakeCommonIntegrationConfig)


def test_integration_helpers_use_integration_settings_object(monkeypatch: pytest.MonkeyPatch):
    class FakeCommon:
        env = "integration"
        healthcheck_enabled = True

    class FakeKeycloak:
        model_fields = {
            "url": None,
            "realm": None,
            "client_id": None,
            "client_secret": None,
            "token_grant_type": None,
            "token_username": None,
            "token_password": None,
        }
        url = "http://keycloak:8080"
        realm = "docmesh"
        client_id = "py-core"
        client_secret = "secret"
        token_grant_type = "password"
        token_username = "tester"
        token_password = "pw"

        @classmethod
        def env_key(cls, field_name: str) -> str:
            return f"KEYCLOAK_{field_name.upper()}"

    class FakePostgres:
        model_fields = {"dsn": None, "host": None, "db": None, "user": None, "password": None}
        dsn = None
        host = "postgres"
        db = "postgres"
        user = "postgres"
        password = "postgres"

        @classmethod
        def env_key(cls, field_name: str) -> str:
            return f"POSTGRES_{field_name.upper()}"

    class FakeLangfuse:
        model_fields = {"enabled": None, "host": None, "public_key": None, "secret_key": None}
        enabled = False
        host = "http://langfuse"
        public_key = "pk"
        secret_key = "sk"

        @classmethod
        def env_key(cls, field_name: str) -> str:
            return f"LANGFUSE_{field_name.upper()}"

    class FakeNats:
        model_fields = {"servers": None}
        servers = ["nats://nats:4222"]

        @classmethod
        def env_key(cls, field_name: str) -> str:
            return f"NATS_{field_name.upper()}"

    class FakeIntegrationSettings:
        docmesh_env = "integration"
        common = FakeCommon()
        keycloak = FakeKeycloak()
        postgres = FakePostgres()
        langfuse = FakeLangfuse()
        nats = FakeNats()
        minio = None
        milvus = None
        ollama = None

    monkeypatch.setattr(test_conftest, "parse_env_file", lambda _: {})
    monkeypatch.setattr(test_conftest, "CommonIntegrationConfig", FakeCommon)
    monkeypatch.setattr(test_conftest, "KeycloakIntegrationDiscoveryConfig", FakeKeycloak)
    monkeypatch.setattr(test_conftest, "KeycloakIntegrationConfig", FakeKeycloak)
    monkeypatch.setitem(test_conftest.INTEGRATION_SERVICE_CONFIG_CLASSES, "keycloak", FakeKeycloak)
    monkeypatch.setitem(test_conftest.INTEGRATION_SERVICE_CONFIG_CLASSES, "postgres", FakePostgres)
    monkeypatch.setitem(test_conftest.INTEGRATION_SERVICE_CONFIG_CLASSES, "langfuse", FakeLangfuse)
    monkeypatch.setitem(test_conftest.INTEGRATION_SERVICE_CONFIG_CLASSES, "nats", FakeNats)

    test_conftest.require_integration_environment()
    assert test_conftest.keycloak_discovery_is_configured() is True
    assert test_conftest.keycloak_token_is_configured() is True
    assert test_conftest.service_is_configured("postgres") is True
    assert test_conftest.service_is_configured("nats") is True
    assert test_conftest.service_is_configured("langfuse") is False
    assert test_conftest.service_env("keycloak")["KEYCLOAK_URL"] == "http://keycloak:8080"
    assert test_conftest.service_env("nats")["NATS_SERVERS"] == "nats://nats:4222"


def test_docs_and_contracts_use_docmesh_env_integration_selector_consistently():
    test_guide = (PROJECT_ROOT / "docs" / "test.md").read_text(encoding="utf-8")
    env_example = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert 'DOCMESH_ENV=integration uv run pytest -q -m integration' in test_guide
    assert '별도 플래그가 아니라 `DOCMESH_ENV=integration`' in test_guide
    assert 'DOCMESH_ENV=development' in env_example


def test_package_root_exports_service_specific_config_api_and_docs_document_loader_flow():
    package_init = (PROJECT_ROOT / "docmesh_py_core" / "__init__.py").read_text(encoding="utf-8")
    api_doc = (PROJECT_ROOT / "docs" / "api.md").read_text(encoding="utf-8")
    examples_doc = (PROJECT_ROOT / "docs" / "examples.md").read_text(encoding="utf-8")
    config_doc = (PROJECT_ROOT / "docs" / "config.md").read_text(encoding="utf-8")
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert '"load_common_config"' not in package_init
    assert '"require_keycloak_config"' not in package_init
    assert '"require_langfuse_config"' not in package_init
    assert '"load_postgres_config"' not in package_init
    assert '"require_postgres_config"' not in package_init
    assert '"require_sqlite_config"' not in package_init
    assert '"load_keycloak_config"' not in package_init
    assert '"load_minio_config"' not in package_init
    assert '"load_milvus_config"' not in package_init
    assert '"load_ollama_config"' not in package_init
    assert '"load_nats_config"' not in package_init
    assert '"load_settings"' not in package_init
    assert '"create_postgres_client"' in package_init
    assert '"create_sqlite_client"' in package_init
    assert '"close_service_clients"' in package_init
    assert '"ServiceConfigs"' in package_init
    assert '"load_service_configs"' in package_init
    assert '"KeycloakConfig"' in package_init
    assert '"CommonConfig"' in package_init
    assert '### 권장 public config entrypoint' in api_doc
    assert 'KeycloakAuthService(keycloak)' in api_doc
    assert 'create_postgres_client' in api_doc
    assert 'close_service_clients' in api_doc
    assert 'CommonConfig()' in api_doc
    assert 'KeycloakConfig()' in api_doc
    assert 'require_postgres_config' not in api_doc
    assert 'require_sqlite_config' not in api_doc
    assert 'load_keycloak_config' not in api_doc
    assert 'load_minio_config' not in api_doc
    assert 'load_milvus_config' not in api_doc
    assert 'load_ollama_config' not in api_doc
    assert 'load_nats_config' not in api_doc
    assert '서비스별 config class를 직접 쓰는 예시' in examples_doc
    assert 'KeycloakConfig()' in examples_doc
    assert '서비스별 config class(`CommonConfig`, `KeycloakConfig`, `LangfuseConfig`, `PostgresConfig`, `SqliteConfig` 등)' in config_doc
    assert 'load_settings' not in config_doc
    assert '이 패키지는 보통 세 가지 방식으로 시작합니다.' in readme
    assert '### A. 서비스별 config class를 직접 사용하는 경로' in readme
    assert 'KeycloakAuthService(keycloak)' in readme
    assert '2. `CommonConfig()` 또는 필요한 `*Config()` 직접 생성' in readme
    assert '`load_service_configs()`가 서비스 묶음 로더의 기본 경로입니다.' in readme
    assert 'create_*_client()' in readme


def test_integration_examples_use_service_specific_keycloak_loader_and_scoped_settings_loading():
    integration_tests = (PROJECT_ROOT / "test_docmesh_py_core" / "test_integration_services.py").read_text(encoding="utf-8")

    assert 'KeycloakIntegrationDiscoveryConfig' in integration_tests
    assert 'KeycloakIntegrationConfig' in integration_tests
    assert 'postgres = PostgresIntegrationConfig()' in integration_tests
    assert 'create_postgres_client(postgres)' in integration_tests
    assert 'with docmesh_env_context(' in integration_tests
    assert 'sqlite = SqliteIntegrationConfig()' in integration_tests
    assert 'nats = NatsIntegrationConfig()' in integration_tests
    assert 'create_nats_client(nats)' in integration_tests


def test_non_integration_test_modules_declare_documented_pytest_slices():

    expected_module_markers = {
        'test_config.py': 'pytestmark = [pytest.mark.unit]',
        'test_env_example.py': 'pytestmark = [pytest.mark.unit]',
        'test_factories.py': 'pytestmark = [pytest.mark.unit]',
        'test_health.py': 'pytestmark = [pytest.mark.unit, pytest.mark.health]',
        'test_keycloak.py': 'pytestmark = [pytest.mark.unit, pytest.mark.keycloak]',
        'test_observability.py': 'pytestmark = [pytest.mark.unit]',
        'test_keycloak_provisioning.py': 'pytestmark = [pytest.mark.unit, pytest.mark.keycloak]',
        'test_project_contract.py': 'pytestmark = [pytest.mark.unit]',
        'test_security.py': 'pytestmark = [pytest.mark.unit, pytest.mark.security, pytest.mark.keycloak]',
    }

    for file_name, marker_snippet in expected_module_markers.items():
        content = (PROJECT_ROOT / 'test_docmesh_py_core' / file_name).read_text(encoding='utf-8')
        assert marker_snippet in content, file_name


def test_security_and_provisioning_test_files_cover_documented_regression_scenarios():
    security_test = (PROJECT_ROOT / 'test_docmesh_py_core' / 'test_security.py').read_text(encoding='utf-8')
    provisioning_test = (PROJECT_ROOT / 'test_docmesh_py_core' / 'test_keycloak_provisioning.py').read_text(encoding='utf-8')

    assert 'test_keycloak_auth_service_masks_temporary_failures' in security_test
    assert 'test_mask_sensitive_value_masks_raw_bearer_tokens' in security_test
    assert 'test_keycloak_provisioner_is_idempotent_when_resources_already_exist' in provisioning_test
    assert 'test_keycloak_provisioner_does_not_delete_unspecified_resources' in provisioning_test
