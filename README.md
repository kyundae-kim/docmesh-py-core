# docmesh-py-core

DocMesh 계열 Python 서비스에서 반복되는 외부 서비스 연동 코드를 공통화하는 SDK입니다.

이 패키지는 다음 책임을 제공합니다.

- 환경변수 기반 설정 로드와 검증
- 서비스별 client 생성 레지스트리
- 공통 health check 집계
- Keycloak access token 발급과 JWT 검증
- 민감정보 마스킹
- 직렬화 / 페이지네이션 / 설정 스냅샷 유틸리티

자세한 소비자 가이드는 [SDK 가이드](docs/sdk.md), 공개 시그니처는 [API 가이드](docs/api.md), 환경변수 계약은 [설정 가이드](docs/config.md), 테스트 전략은 [테스트 가이드](docs/test.md)를 참고하세요.

---

## 설치

### 저장소를 직접 열어 작업할 때

```bash
uv sync
```

### 다른 프로젝트에서 GitHub 소스로 추가할 때

```bash
uv add git+https://github.com/<org>/<repo>.git
```

특정 브랜치, 태그, 커밋을 고정하려면 예를 들어 다음 형태를 사용합니다.

```bash
uv add git+https://github.com/<org>/<repo>.git@main
uv add git+https://github.com/<org>/<repo>.git@v0.1.1
uv add git+https://github.com/<org>/<repo>.git@<commit-sha>
```

패키지 이름을 명시적으로 별칭처럼 적고 싶다면 다음 형태도 사용할 수 있습니다.

```bash
uv add docmesh-py-core @ git+https://github.com/<org>/<repo>.git
```

Python 요구사항:

- Python 3.11+

주요 런타임 의존성:

- `pydantic-settings`
- `sqlalchemy`
- `minio`
- `pymilvus`
- `ollama`
- `langfuse`
- `nats-py`
- `pyjwt[crypto]`

---

## 언제 쓰면 좋은가

다음과 같은 소비 프로젝트에 적합합니다.

- FastAPI / Flask API 서버
- background worker / consumer
- 배치 / CLI 애플리케이션
- PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS, Keycloak을 함께 쓰는 서비스

특히 아래 상황에서 유용합니다.

- 서비스별 환경변수 검증을 중복 구현하고 싶지 않을 때
- startup health check 패턴을 통일하고 싶을 때
- Keycloak 인증 / JWT 검증 코드를 공통화하고 싶을 때
- 로컬에서는 SQLite, 다른 환경에서는 PostgreSQL 같은 구성을 가져가고 싶을 때

---

## 빠른 시작 전 알아둘 점

`load_settings()`는 데이터베이스 설정만 읽지 않습니다. 현재 구현 기준으로 아래 설정을 함께 검증합니다.

- Keycloak
- MinIO
- Milvus
- Ollama
- NATS
- Langfuse (`LANGFUSE_ENABLED=false`이면 비활성화 가능)
- PostgreSQL / SQLite (둘 다 optional)

따라서 README의 예제를 그대로 실행하려면 데이터베이스 변수만이 아니라 위 서비스의 필수 환경변수도 준비되어 있어야 합니다.

전체 예시 변수 목록은 저장소 루트의 [`.env.example`](.env.example)에 있고, 세부 규칙은 [docs/config.md](docs/config.md)에 정리되어 있습니다.

---

## 기본 사용 흐름

소비 애플리케이션에서의 권장 순서는 다음과 같습니다.

1. 환경변수 준비
2. `load_settings()` 호출
3. `ServiceFactoryRegistry(settings)` 생성
4. 필요한 서비스만 `create_client()`로 생성
5. startup 또는 실제 사용 전에 `check()` 호출
6. 종료 시 `close_all()` 호출

예시:

```python
from os import environ

from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)

postgres = registry.create_client("postgres")
postgres.check()

with postgres.connect() as conn:
    conn.exec_driver_sql("SELECT 1")

registry.close_all()
```

SQLite를 사용할 때는 서비스명만 바꾸면 됩니다.

```python
from os import environ

from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)

sqlite = registry.create_client("sqlite")
sqlite.check()

with sqlite.connect() as conn:
    conn.exec_driver_sql("SELECT 1")

registry.close_all()
```

---

## 루트 import 예시

일반 소비 코드는 하위 모듈보다 패키지 루트 import를 우선 권장합니다.

```python
from docmesh_py_core import (
    ConfigError,
    KeycloakAuthService,
    ServiceFactoryRegistry,
    Settings,
    check_all_services,
    load_settings,
)
```

전체 공개 API는 [docs/api.md](docs/api.md)를 참고하세요.

---

## 주요 서비스 계약

### PostgreSQL / SQLite

- `registry.create_client("postgres")` → `ServiceClientWrapper`
- `registry.create_client("sqlite")` → `ServiceClientWrapper`
- 현재 기본 health check는 둘 다 `SELECT 1`

### MinIO / Milvus / Ollama / Langfuse

- MinIO health check → `list_buckets()`
- Milvus health check → `list_collections()`
- Ollama health check → `ps()`
- Langfuse health check → `auth_check()`
- Langfuse는 `LANGFUSE_ENABLED=false`이면 `create_client("langfuse")` 결과가 `None`

### NATS

`registry.create_client("nats")`는 연결된 동기 client가 아니라 `NatsConnectionBuilder`를 반환합니다.

```python
import asyncio

builder = registry.create_client("nats")
asyncio.run(builder.check())
```

현재 `check()`는 connect 후 `flush()`까지 수행하고 연결을 정리합니다.

### Keycloak

```python
from docmesh_py_core import KeycloakAuthService

auth = KeycloakAuthService(settings)
token = auth.fetch_access_token()
```

JWT 검증 예시:

```python
from docmesh_py_core import KeycloakAuthService

auth = KeycloakAuthService(settings, allowed_algorithms=["RS256"])
user = auth.extract_user_info(raw_jwt)
```

---

## Health check 집계

여러 서비스의 readiness를 한 번에 점검할 때는 `check_all_services()`를 사용합니다.

```python
from docmesh_py_core import check_all_services

result = check_all_services(
    {
        "postgres": postgres.check,
        "minio": minio.check,
    },
    required_services={"postgres"},
)
```

병렬 점검이 필요하면 `parallel=True`를 사용할 수 있습니다.

```python
parallel_result = check_all_services(
    {
        "postgres": postgres.check,
        "minio": minio.check,
    },
    required_services={"postgres"},
    parallel=True,
)
```

---

## 환경변수 원칙

- 모든 설정은 환경변수에서 읽습니다.
- 공백 문자열은 값이 없는 것으로 간주합니다.
- boolean 문자열은 `true` / `false`로 해석합니다.
- 리스트형 값은 주로 쉼표 구분 문자열로 입력합니다.
- 운영 환경(`DOCMESH_ENV=production|prod`)에서는 일부 비보안 설정이 거부됩니다.

서비스별 필수 / 선택 / 조건부 필수 변수는 [docs/config.md](docs/config.md)를 참고하세요.

---

## 테스트

기본 단위 테스트 실행:

```bash
uv run pytest -q test_docmesh_py_core
```

integration 테스트 실행:

```bash
DOCMESH_ENV=integration uv run pytest -q -m integration
```

특정 파일만 실행할 수도 있습니다.

```bash
uv run pytest -q test_docmesh_py_core/test_factories.py
```

Pytest 마커는 `pyproject.toml`에 등록되어 있으며 `unit`, `integration`, `security`, `keycloak`, `health`를 사용합니다.

---

## 문서 읽는 순서

처음 보는 소비자라면 다음 순서를 권장합니다.

1. [README.md](README.md)
2. [docs/sdk.md](docs/sdk.md)
3. [docs/config.md](docs/config.md)
4. [docs/api.md](docs/api.md)
5. [docs/test.md](docs/test.md)
