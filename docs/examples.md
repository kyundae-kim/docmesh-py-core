# docmesh-py-core Examples

이 문서는 `docmesh-py-core`를 실제 애플리케이션에 붙일 때 바로 복사·응용할 수 있는 예시를 제공합니다.

- 공개 API 설명은 [api.md](./api.md)
- 환경변수 계약은 [config.md](./config.md)
- 기본 소개는 [README](../README.md)

## 1. 가장 작은 성공 예제

```python
from os import environ

from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)

postgres = registry.create_client("postgres")
postgres.check()

registry.close_all()
```

적합한 상황:

- 시작 시 설정 유효성만 확인하고 싶을 때
- 서비스 연결 smoke test가 필요할 때

## 2. FastAPI startup / shutdown 예시

```python
from contextlib import asynccontextmanager
from os import environ

from fastapi import FastAPI

from docmesh_py_core import ServiceFactoryRegistry, load_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings(environ)
    registry = ServiceFactoryRegistry(settings)

    app.state.settings = settings
    app.state.registry = registry

    # 필수 서비스만 시작 시점에 확인
    app.state.registry.create_client("postgres").check()
    app.state.registry.create_client("minio").check()

    try:
        yield
    finally:
        registry.close_all()


app = FastAPI(lifespan=lifespan)
```

포인트:

- `load_settings()`는 startup 시 한 번만 호출
- `ServiceFactoryRegistry`는 앱 수명주기 동안 재사용
- 종료 시 `close_all()` 호출

## 3. Health endpoint 구성 예시

```python
from fastapi import APIRouter, Request

from docmesh_py_core import HealthCheckError, check_all_services

router = APIRouter()


@router.get("/health")
def health(request: Request):
    registry = request.app.state.registry

    postgres = registry.create_client("postgres")
    minio = registry.create_client("minio")
    ollama = registry.create_client("ollama")

    try:
        result = check_all_services(
            {
                "postgres": postgres.check,
                "minio": minio.check,
                "ollama": ollama.check,
            },
            required_services={"postgres", "minio"},
            parallel=True,
        )
    except HealthCheckError as exc:
        return {
            "ok": False,
            "error": str(exc),
        }

    return {
        "ok": result.ok,
        "services": [
            {
                "service": item.service,
                "ok": item.ok,
                "latency_ms": item.latency_ms,
                "error": item.error,
            }
            for item in result.services
        ],
    }
```

포인트:

- `required_services`로 필수/선택 서비스를 구분
- `parallel=True`면 독립 서비스 health check를 병렬 수행
- 오류 메시지는 내부적으로 민감정보 마스킹 적용

## 4. SQLite 로컬 개발 예시

환경변수 예:

```env
DOCMESH_ENV=development
KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=docmesh-backend
KEYCLOAK_CLIENT_SECRET=replace-me
SQLITE_PATH=./data/docmesh.sqlite3
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=replace-me
MINIO_SECRET_KEY=replace-me
MILVUS_URI=http://milvus.example.com:19530
OLLAMA_HOST=http://ollama.example.com:11434
LANGFUSE_ENABLED=false
NATS_SERVERS=nats://localhost:4222
```

사용 코드:

```python
from os import environ

from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)

sqlite = registry.create_client("sqlite")
sqlite.check()

with sqlite.connect() as conn:
    row = conn.exec_driver_sql("SELECT 1").scalar_one()
    print(row)

registry.close_all()
```

포인트:

- `SQLITE_PATH=:memory:` 도 가능
- 상대경로는 앱 작업 디렉터리 기준
- 로컬 개발에서는 `LANGFUSE_ENABLED=false`로 선택 기능을 꺼둘 수 있음

## 5. Keycloak access token 획득 예시

### client credentials grant

```python
from os import environ

from docmesh_py_core import KeycloakAuthService, load_settings

settings = load_settings(environ)
auth = KeycloakAuthService(settings)

token = auth.fetch_access_token()
print(token.access_token)
print(token.token_type)
print(token.expires_in)
```

### password grant

설정에서는 grant type만 지정하고, 실제 사용자 credential은 함수 인자로 전달합니다.

```env
KEYCLOAK_TOKEN_GRANT_TYPE=password
```

```python
from os import environ

from docmesh_py_core import KeycloakAuthService, load_settings

settings = load_settings(environ)
auth = KeycloakAuthService(settings)

token = auth.fetch_access_token(
    username="alice",
    password="replace-me",
)
print(token.access_token)
```

## 6. Keycloak JWT 검증 예시 (RS256)

Keycloak 기본 배포는 RS256 토큰을 자주 사용하므로, 검증 시 허용 알고리즘을 명시하는 것이 안전합니다.

```python
from os import environ

from docmesh_py_core import KeycloakAuthService, TokenValidationError, load_settings

settings = load_settings(environ)
auth = KeycloakAuthService(settings, allowed_algorithms=["RS256"])

try:
    user = auth.extract_user_info("Bearer <jwt>")
except TokenValidationError as exc:
    print("token invalid:", exc)
else:
    print(user.sub)
    print(user.preferred_username)
    print(user.realm_roles)
    print(user.client_roles)
```

포인트:

- `allowed_algorithms`를 지정하지 않으면 기본값은 `['HS256']`
- RS256 검증 시 JWKS를 자동 조회/캐시
- audience 검증이 필요하면 `KEYCLOAK_AUDIENCE` 설정

## 7. Langfuse optional 분기 예시

```python
from os import environ

from docmesh_py_core import ServiceFactoryRegistry, load_settings

settings = load_settings(environ)
registry = ServiceFactoryRegistry(settings)

langfuse = registry.create_client("langfuse")
if langfuse is not None:
    langfuse.check()
else:
    print("Langfuse disabled")
```

포인트:

- `LANGFUSE_ENABLED=false`면 `create_client("langfuse")` 결과가 `None`
- 소비 애플리케이션은 optional dependency처럼 다루는 것이 좋음

## 8. NATS async 연결 예시

```python
import asyncio
from os import environ

from docmesh_py_core import ServiceFactoryRegistry, load_settings


async def main() -> None:
    settings = load_settings(environ)
    registry = ServiceFactoryRegistry(settings)

    builder = registry.create_client("nats")

    # 연결 가능 여부만 확인
    await builder.check()

    # 실제 장기 연결이 필요하면 connect() 결과를 직접 관리
    client = await builder.connect()
    try:
        await client.flush()
        print("connected")
    finally:
        drain = getattr(client, "drain", None)
        if callable(drain):
            await drain()
        else:
            close = getattr(client, "close", None)
            if callable(close):
                result = close()
                if asyncio.iscoroutine(result):
                    await result


asyncio.run(main())
```

포인트:

- `nats`는 `ServiceClientWrapper`가 아니라 `NatsConnectionBuilder`
- `check()`는 연결 후 `flush()` 확인 뒤 정리
- 지속 연결은 `connect()` 반환값을 애플리케이션이 직접 수명 관리해야 함

## 9. 재시도 유틸리티 예시

```python
from docmesh_py_core import retry_call


class TemporaryError(RuntimeError):
    pass


attempts = {"count": 0}


def flaky_operation() -> str:
    attempts["count"] += 1
    if attempts["count"] < 3:
        raise TemporaryError("temporary failure")
    return "ok"


result = retry_call(
    flaky_operation,
    retry_on=(TemporaryError,),
    max_attempts=3,
)
print(result)
```

포인트:

- `retry_call()`은 동기 함수용 유틸리티
- 재시도 간격은 지수 백오프
- 영구 오류는 `retry_on`에 넣지 않는 것이 원칙

## 10. 예시 선택 가이드

- 웹 API 서버 시작/종료 → **FastAPI startup / shutdown 예시**
- readiness/liveness 구성 → **Health endpoint 예시**
- 로컬 경량 저장소 → **SQLite 예시**
- 인증 서버 연동 → **Keycloak token / JWT 예시**
- 선택형 observability → **Langfuse optional 예시**
- 비동기 메시징 → **NATS async 예시**

## 11. 관련 문서

- API 세부 계약: [api.md](./api.md)
- 환경변수/활성화 규칙: [config.md](./config.md)
- 테스트 전략: [test.md](./test.md)
- 상위 개요: [README](../README.md)
