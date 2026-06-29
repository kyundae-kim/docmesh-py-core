# docmesh-py-core

`docmesh-py-core`는 DocMesh 계열 Python 애플리케이션이 외부 서비스를 **일관된 설정 방식**, **공통 클라이언트 팩토리**, **표준 헬스체크**, **안전한 인증/마스킹 정책**으로 연결할 수 있게 돕는 공개용 라이브러리입니다.

이 패키지는 다음 문제를 해결합니다.

- 서비스별 환경변수 로딩/검증 중복
- PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS, Keycloak 연동 방식 불일치
- 연결 실패와 재시도 정책의 파편화
- 토큰, 비밀번호, DSN 같은 민감정보의 로그 노출 위험
- Keycloak 토큰 획득/JWT 검증/사용자 정보 추출 코드 중복

## 지원 범위

v0.1.x 기준 주요 기능:

- 환경변수 기반 설정 로딩 및 검증
- 서비스별 클라이언트 생성 인터페이스
- 개별/집계 헬스체크
- Keycloak Access Token 획득
- JWT 검증 및 표준 사용자 정보 추출
- Keycloak Realm/Client/Role 프로비저닝
- 민감정보 마스킹 유틸리티

지원 외부 서비스:

| 서비스 | 용도 |
| --- | --- |
| Keycloak | 인증, JWT 검증, 프로비저닝 |
| PostgreSQL | 메타데이터/업무 데이터 저장 |
| SQLite | 로컬/테스트 저장소 |
| MinIO | 객체 저장소 |
| Milvus | 벡터 저장/검색 |
| Ollama | 모델 호출 |
| Langfuse | LLM 트레이싱/관측성 |
| NATS | 메시징 |

## 설치

### uv

```bash
uv add git+https://github.com/kyundae-kim/docmesh-py-core.git
```

브랜치/태그/커밋을 고정하려면:

```bash
uv add git+https://github.com/kyundae-kim/docmesh-py-core.git@main
uv add git+https://github.com/kyundae-kim/docmesh-py-core.git@v0.1.2
```

### 저장소를 직접 열어 작업할 때

```bash
uv sync
```

요구사항:

- Python 3.11+

## 빠른 시작

가장 일반적인 사용 순서는 다음과 같습니다.

1. 환경변수 준비
2. `load_settings()`로 설정 로딩/검증
3. `ServiceFactoryRegistry(settings)` 생성
4. 필요한 서비스만 `create_client()`로 생성
5. 시작 시점에 `check()` 또는 `check_all_services()` 호출
6. 종료 시 `close_all()` 호출

### 예시: PostgreSQL 사용

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

### 예시: SQLite 사용

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

### 예시: Keycloak 토큰 획득 및 사용자 정보 추출

```python
from os import environ

from docmesh_py_core import KeycloakAuthService, load_settings

settings = load_settings(environ)
auth = KeycloakAuthService(settings)

token = auth.fetch_access_token()
user = auth.extract_user_info("Bearer <jwt>")

print(token.token_type, token.expires_in)
print(user.sub, user.preferred_username)
```

## 공개 API 진입점

일반 소비 코드는 패키지 루트 import를 권장합니다.

```python
from docmesh_py_core import (
    AccessTokenResult,
    AuthenticatedUser,
    ConfigError,
    HealthCheckError,
    KeycloakAuthService,
    KeycloakProvisioner,
    KeycloakTokenAuthenticationError,
    KeycloakTokenConfigurationError,
    KeycloakTokenError,
    KeycloakTokenTemporaryError,
    NatsConnectionBuilder,
    ServiceClientError,
    ServiceClientWrapper,
    ServiceClientWrapperError,
    ServiceFactoryRegistry,
    Settings,
    SqliteConfig,
    TokenValidationError,
    UnsupportedServiceError,
    build_service_log_event,
    check_all_services,
    load_settings,
    mask_sensitive_value,
    retry_call,
)
```

전체 공개 시그니처는 [docs/api.md](docs/api.md)를 참고하세요.

## 설정 원칙

- 모든 설정은 환경변수에서 읽습니다.
- 공백 문자열은 미설정으로 처리합니다.
- Boolean 값은 `true` / `false`로 해석합니다.
- 민감정보는 로그와 예외 메시지에서 마스킹해야 합니다.
- 운영 환경에서는 TLS 검증을 기본으로 유지해야 합니다.
- 서비스별 timeout/retry는 각 서비스 환경변수로 관리합니다.

자세한 환경변수 목록은 [docs/config.md](docs/config.md)를 참고하세요.

## 헬스체크 예시

```python
from docmesh_py_core import check_all_services

result = check_all_services(
    {
        "postgres": postgres.check,
        "minio": minio.check,
    },
    required_services={"postgres"},
    parallel=True,
)

print(result.ok)
for item in result.services:
    print(item.service, item.ok, item.latency_ms, item.error)
```

## 문서 읽는 순서

새로 도입하는 팀이라면 다음 순서를 권장합니다.

1. `README.md`
2. [docs/config.md](docs/config.md)
3. [docs/api.md](docs/api.md)
4. [docs/examples.md](docs/examples.md)
5. [docs/srs.md](docs/srs.md)
6. [docs/test.md](docs/test.md)

## 비목표

이 패키지는 다음을 직접 해결하지 않습니다.

- 외부 서비스 설치/배포 자동화
- DB 스키마/마이그레이션 관리
- 애플리케이션 도메인 로직 구현
- MinIO Bucket, Milvus Collection, NATS Stream의 업무 정책 관리
- Ollama 모델 다운로드/수명주기 관리

## 테스트

```bash
uv run pytest -q test_docmesh_py_core
```

integration 테스트:

```bash
DOCMESH_ENV=integration uv run pytest -q -m integration
```
