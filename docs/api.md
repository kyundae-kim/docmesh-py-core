# docmesh-py-core API Reference

이 문서는 `docmesh-py-core`의 공개 API 레퍼런스입니다.

- 사용 흐름은 [README](../README.md)
- 환경변수/설정 규칙은 [config.md](./config.md)
- 실제 통합 예시는 [examples.md](./examples.md)

## 1. Public imports

패키지 루트에서 바로 import 가능한 대표 공개 API:

```python
from docmesh_py_core import (
    AccessTokenResult,
    AuthenticatedUser,
    CommonConfig,
    ConfigError,
    HealthCheckError,
    KeycloakAuthService,
    KeycloakConfig,
    KeycloakProvisioner,
    KeycloakTokenAuthenticationError,
    KeycloakTokenConfigurationError,
    KeycloakTokenError,
    KeycloakTokenTemporaryError,
    LangfuseConfig,
    MinioConfig,
    MilvusConfig,
    NatsConnectionBuilder,
    NatsConfig,
    OllamaConfig,
    PostgresConfig,
    ServiceClientError,
    ServiceClientWrapper,
    ServiceClientWrapperError,
    ServiceConfigs,
    SqliteConfig,
    TokenValidationError,
    apply_langfuse_defaults,
    build_service_log_event,
    check_all_services,
    close_service_clients,
    create_keycloak_client,
    create_langfuse_client,
    create_milvus_client,
    create_minio_client,
    create_nats_client,
    create_ollama_client,
    create_postgres_client,
    create_sqlite_client,
    load_common_config,
    load_service_configs,
    load_settings,
    mask_sensitive_value,
    require_keycloak_config,
    require_langfuse_config,
    require_milvus_config,
    require_minio_config,
    require_nats_config,
    require_ollama_config,
    retry_call,
    validate_runtime_security,
)
```

> 위 목록은 `docmesh_py_core/__init__.py`의 `__all__` 기준입니다.

## 1.1 권장 호출 순서

대부분의 소비 애플리케이션은 아래 순서로 SDK를 사용합니다.

1. 환경변수 준비
2. `load_common_config()` 또는 `load_service_configs()` 호출
3. 필요한 서비스만 `create_*_client()`로 조립
4. 시작 시점에 `check()` 또는 `check_all_services()` 실행
5. 종료 시 `close_service_clients()` 또는 개별 `close()` 호출

주의:

- `nats`만 예외적으로 `NatsConnectionBuilder`를 반환하며, 실제 연결은 `await connect()/ping()/check()`에서 일어납니다.
- `langfuse`는 `LANGFUSE_ENABLED=false`면 `None`이 될 수 있으므로 소비 코드에서 분기 처리가 필요합니다.

## 2. Service config API

### 권장 public config entrypoint

서비스별 설정만 필요하면 aggregate `ServiceConfigs`보다 서비스별 config entrypoint를 우선 사용하는 것을 권장합니다.

- 공통: `load_common_config() -> CommonConfig`
- Keycloak: `require_keycloak_config()`
- PostgreSQL: `PostgresConfig()`
- SQLite: `SqliteConfig()`
- MinIO: `require_minio_config()`
- Milvus: `require_milvus_config()`
- Ollama: `require_ollama_config()`
- Langfuse: `require_langfuse_config(common=...)`
- NATS: `require_nats_config()`

규칙:

- `require_*`는 필수 설정이 없으면 `ConfigError`를 발생시킵니다.
- `PostgresConfig()`와 `SqliteConfig()`는 필수 서비스 설정 모델로 직접 생성합니다.
- `load_service_configs()`는 선택된 `postgres`/`sqlite`/`langfuse`도 필수 서비스로 검증합니다.
- `load_settings()`는 기존 호출부를 위한 compatibility alias입니다.

예시:

```python
from docmesh_py_core import KeycloakAuthService, load_common_config, require_keycloak_config

common = load_common_config()
keycloak = require_keycloak_config()

assert common.env in {"development", "integration", "production"}

auth = KeycloakAuthService(keycloak)
```

### `load_service_configs(*, services=None) -> ServiceConfigs`

현재 프로세스 환경변수에서 설정을 읽고 검증합니다.

주요 동작:

- `services=None`이면 지원 서비스 전체를 검증합니다.
- `services={...}`를 주면 지정한 서비스만 검증하고, 나머지 필드는 `None`으로 둡니다.
- 선택된 서비스에서 필수 env가 없으면 `ConfigError`가 발생합니다.
- 검증 실패 시 `ConfigError`가 발생합니다.
- `LANGFUSE_ENVIRONMENT`가 비어 있으면 `DOCMESH_ENV` 값을 상속합니다.

partial loading 예시:

```python
from docmesh_py_core import create_nats_client, create_sqlite_client, load_service_configs

settings = load_service_configs(
    services={"sqlite", "nats"},
)

sqlite = create_sqlite_client(settings.sqlite)
builder = create_nats_client(settings.nats)

assert settings.keycloak is None
assert settings.minio is None
```

### `ServiceConfigs`

패키지의 서비스 묶음 dataclass입니다.

하위 설정 필드:

- `settings.common`
- `settings.keycloak`
- `settings.postgres` (`services`에 선택되지 않으면 `None`)
- `settings.sqlite` (`services`에 선택되지 않으면 `None`)
- `settings.minio`
- `settings.milvus`
- `settings.ollama`
- `settings.langfuse`
- `settings.nats`

## 3. Client creation API

현재 권장 경로는 서비스별 `create_*_client()` 함수입니다.

### `create_keycloak_client(config: KeycloakConfig) -> ServiceClientWrapper`

- 내부적으로 `KeycloakAuthService(config)`를 생성합니다.
- `check()`는 access token fetch를 사용합니다.

### `create_postgres_client(config: PostgresConfig) -> ServiceClientWrapper`

- SQLAlchemy engine을 생성합니다.
- `check()`는 `SELECT 1` 실행입니다.
- `close()`는 내부 `dispose()`를 호출합니다.

### `create_sqlite_client(config: SqliteConfig) -> ServiceClientWrapper`

- SQLite engine을 생성합니다.
- `busy_timeout_ms`, `enable_wal`, `readonly`를 반영합니다.
- `check()`는 `SELECT 1` 실행입니다.

### `create_minio_client(config: MinioConfig) -> ServiceClientWrapper`

- `check()`는 `list_buckets()`를 호출합니다.

### `create_milvus_client(config: MilvusConfig) -> ServiceClientWrapper`

- `check()`는 `list_collections()`를 호출합니다.

### `create_ollama_client(config: OllamaConfig) -> ServiceClientWrapper`

- `check()`는 `ps()`를 호출합니다.

### `create_langfuse_client(config: LangfuseConfig) -> ServiceClientWrapper | None`

- `LANGFUSE_ENABLED=false`면 `None`을 반환합니다.
- 활성화 시 `check()`는 `auth_check()`를 호출합니다.

### `create_nats_client(config: NatsConfig) -> NatsConnectionBuilder`

- 즉시 연결하지 않습니다.
- 실제 네트워크 연결은 `await builder.connect()` / `await builder.check()`에서 일어납니다.

예시:

```python
from docmesh_py_core import create_postgres_client, load_service_configs

settings = load_service_configs(services={"postgres"})
postgres = create_postgres_client(settings.postgres)
postgres.check()
postgres.close()
```

## 4. 공통 wrapper / helper API

### `ServiceClientWrapper`

서비스 클라이언트를 표준 인터페이스로 감싸는 wrapper입니다.

주요 메서드:

- `check()` / `ping()`
- `close()`
- `__getattr__()` 위임

### `close_service_clients(clients: Iterable[Any]) -> None`

여러 wrapper/client에 대해 `close()`를 순회 호출합니다. `None` 값은 무시합니다.

예시:

```python
from docmesh_py_core import close_service_clients

close_service_clients([postgres, minio, langfuse])
```

### `ServiceClientError`

서비스 생성/헬스체크 표준 오류의 베이스 타입입니다.

### `ServiceClientWrapperError`

`ServiceClientWrapper.check()`에서 발생한 오류를 표준화한 타입입니다.

## 5. Health / security / retry API

### `check_all_services(checks, required_services=None, parallel=False)`

서비스 헬스체크 함수를 모아 실행합니다.

### `mask_sensitive_value(value: str | None) -> str | None`

비밀번호, bearer token, secret 같은 민감정보를 로그 친화적으로 마스킹합니다.

### `retry_call(...)`

일시적 실패에 대한 재시도 유틸리티입니다.
