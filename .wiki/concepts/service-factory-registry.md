---
title: 서비스 팩토리 레지스트리
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [factory-pattern, service-connection, sdk-design, async]
sources: []
confidence: high
---

# 서비스 팩토리 레지스트리

`factories.py`의 `ServiceFactoryRegistry`는 [[settings-system]]의 설정을 받아
서비스 클라이언트를 생성하고 수명주기를 관리하는 팩토리 레지스트리다.

## 핵심 타입

### ServiceClientWrapper

모든 서비스 클라이언트를 감싸는 어댑터. 일관된 헬스체크 인터페이스를 제공한다.

```python
@dataclass
class ServiceClientWrapper:
    client: Any               # 실제 클라이언트 (Minio, MilvusClient 등)
    healthcheck: HealthCheck  # () -> Any: 연결 확인 함수
    close_fn: Callable | None # 명시적 close (기본: client.close())

    def ping() -> Any        # healthcheck() 호출
    def check() -> Any       # ping() 별칭
    def close() -> Any       # close_fn 또는 client.close() 호출
    def __getattr__          # 미정의 속성은 inner client로 위임
```

`__getattr__` 위임 덕분에 `wrapper.list_buckets()` 처럼 내부 클라이언트 메서드를
래퍼 API로 직접 호출할 수 있다.

### NatsConnectionBuilder

NATS는 비동기 연결이 필요해 `ServiceClientWrapper` 대신 별도 빌더를 사용한다.

```python
@dataclass(frozen=True)
class NatsConnectionBuilder:
    servers: list[str]
    name: str
    connect_timeout_seconds: int
    max_reconnect_attempts: int
    user: str | None
    password: str | None
    token: str | None
    creds_file: str | None

    async def connect() -> nats.NATS  # 실제 연결 반환
```

NATS 클라이언트는 `await builder.connect()` 로 사용자가 직접 연결한다.
팩토리가 연결을 소유하지 않으므로 asyncio 이벤트 루프 수명주기와 결합되지 않는다.

## ServiceFactoryRegistry 사용법

```python
from docmesh_py_core import ServiceFactoryRegistry, load_settings
import os

settings = load_settings(os.environ)
registry = ServiceFactoryRegistry(settings)

# 개별 클라이언트 획득
minio   = registry.get("minio")    # → ServiceClientWrapper
milvus  = registry.get("milvus")   # → ServiceClientWrapper
postgres = registry.get("postgres") # → ServiceClientWrapper
keycloak = registry.get("keycloak") # → ServiceClientWrapper(KeycloakAuthService)
nats_builder = registry.get("nats") # → NatsConnectionBuilder

# 지원 서비스 확인
registry.list_services()  # → ['keycloak', 'postgres', 'minio', 'milvus', 'ollama', 'langfuse', 'nats']

# 모든 서비스 헬스체크
checks = registry.health_checks()  # → Mapping[str, CheckFn]
```

## 지원 서비스 및 헬스체크 전략

| 서비스 | 클라이언트 | 헬스체크 메서드 | 반환 타입 |
|--------|-----------|----------------|-----------|
| keycloak | `KeycloakAuthService` | `fetch_access_token()` | `AccessTokenResult` |
| postgres | SQLAlchemy `Engine` | `SELECT 1` 실행 | - |
| minio | `minio.Minio` | `list_buckets()` | `list[Bucket]` |
| milvus | `MilvusClient` | `list_collections()` | `list[str]` |
| ollama | `ollama.Client` | `ps()` | 실행 중 모델 목록 |
| langfuse | `langfuse.Langfuse` | `auth_check()` | - |
| nats | `NatsConnectionBuilder` | (빌더 반환, 연결 없음) | - |

## 서비스 추가 패턴

새 서비스를 추가할 때:

1. `config.py`에 `XxxConfig(DocmeshBaseSettings)` 추가 (접두사 관례 준수)
2. `Settings` 집계 모델에 필드 추가
3. `factories.py`에 `_build_xxx_client(config) -> ServiceClientWrapper` 추가
4. `_service_map` dict에 서비스명 → (config_attr, builder) 등록
5. 위키: [[settings-system]] 환경 변수 표 업데이트

## Langfuse 특이 사항

`langfuse.enabled=false`면 `_build_langfuse_client`가 `None`을 반환한다.
`health_checks()` 수집 시 `None`인 서비스는 제외되므로,
비활성화된 서비스의 헬스체크는 자동으로 건너뛴다.

## NATS 비동기 종료

```python
async def cleanup(nats_client):
    await _close_async_client(nats_client)
    # drain() → awaitable 이면 await, 아니면 close() 시도
```

## 관련 개념

- [[settings-system]] — 설정 공급 계층
- [[health-check-pattern]] — 헬스체크 결과 집계
- [[keycloak-auth-flow]] — keycloak 서비스의 실제 기능
- [[nats]] — NATS 서비스 상세
