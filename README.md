# docmesh-py-core

`docmesh-py-core`는 DocMesh 계열 Python 애플리케이션이 외부 서비스를 **일관된 설정 방식**, **서비스별 생성 함수**, **표준 헬스체크**, **안전한 인증/마스킹 정책**으로 연결할 수 있게 돕는 공개용 라이브러리입니다.

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

이 패키지는 보통 세 가지 방식으로 시작합니다.

### A. 서비스별 config class를 직접 사용하는 경로

적합한 상황:

- 특정 서비스 SDK만 직접 쓰면 충분함
- aggregate `ServiceConfigs` 묶음 전체를 들고 다니고 싶지 않음
- 기능 단위로 config 의존 범위를 최소화하고 싶음

기본 순서:

1. 환경변수 준비
2. `CommonConfig()` 또는 필요한 `*Config()` 직접 생성
3. 필요한 서비스 객체를 해당 config로 직접 생성
4. 필요한 동작만 수행

#### 예시: Keycloak 토큰 획득

```python
from docmesh_py_core import CommonConfig, KeycloakAuthService, KeycloakConfig

common = CommonConfig()
keycloak = KeycloakConfig()
auth = KeycloakAuthService(keycloak)

token = auth.fetch_access_token()

print(common.env)
print(token.token_type, token.expires_in)
```

포인트:

- 서비스별 `*Config()` 직접 생성은 pydantic `ValidationError`를 그대로 발생시킵니다.
- `KeycloakAuthService`, `KeycloakProvisioner`는 신규 코드에서 서비스별 config 직접 주입을 권장합니다.

### B. aggregate settings를 로드한 뒤 서비스별 create 함수로 조립하는 경로

적합한 상황:

- 애플리케이션이 이 라이브러리의 표준 서비스 묶음을 전반적으로 사용함
- 시작 시점에 전체 환경 구성을 한 번에 검증하고 싶음
- 배포/운영에서 누락된 env를 초기에 빠르게 발견하고 싶음

기본 순서:

1. 환경변수 준비
2. `load_service_configs()`로 전체 설정 로딩/검증
3. 필요한 서비스만 `create_*_client()`로 생성
4. 시작 시점에 `check()` 또는 `check_all_services()` 호출
5. 종료 시 `close_service_clients()` 또는 개별 `close()` 호출

#### 예시: PostgreSQL 사용

```python
from docmesh_py_core import close_service_clients, create_postgres_client, load_service_configs

settings = load_service_configs(services={"postgres"})
postgres = create_postgres_client(settings.postgres)

postgres.check()

with postgres.connect() as conn:
    conn.exec_driver_sql("SELECT 1")

close_service_clients([postgres])
```

#### 예시: SQLite 사용

```python
from docmesh_py_core import create_sqlite_client, load_service_configs

settings = load_service_configs(services={"sqlite"})
sqlite = create_sqlite_client(settings.sqlite)

sqlite.check()

with sqlite.connect() as conn:
    conn.exec_driver_sql("SELECT 1")

sqlite.close()
```

### C. 필요한 서비스만 선택 로딩하는 경로

적합한 상황:

- 공용 라이브러리/모듈이 특정 서비스 몇 개만 사용함
- 사용하지 않는 서비스 env까지 강제하고 싶지 않음
- 테스트/로컬 도구/부분 기능 앱에서 설정 결합을 줄이고 싶음

기본 순서:

1. 환경변수 준비
2. `load_service_configs(services={...})`로 필요한 서비스만 선택 로딩
3. 로드된 설정만 `create_*_client()`로 조립
4. 필요한 검증만 수행
5. 종료 시 개별 `close()` 또는 `close_service_clients()` 호출

#### 예시: SQLite + NATS만 사용

```python
from docmesh_py_core import create_nats_client, create_sqlite_client, load_service_configs

settings = load_service_configs(
    services={"sqlite", "nats"},
)

sqlite = create_sqlite_client(settings.sqlite)
sqlite.check()

builder = create_nats_client(settings.nats)

assert settings.keycloak is None
assert settings.minio is None
```

포인트:

- `services`를 지정하면 필요한 서비스만 검증/로딩합니다.
- 선택되지 않은 서비스 설정 필드는 `None`입니다.
- `create_nats_client(...)`는 `NatsConnectionBuilder`를 반환합니다.

### 예시: 서비스별 Keycloak config로 토큰 획득 및 사용자 정보 추출

```python
from docmesh_py_core import KeycloakAuthService, KeycloakConfig

keycloak = KeycloakConfig()
auth = KeycloakAuthService(keycloak)

token = auth.fetch_access_token()
user = auth.extract_user_info("Bearer <jwt>")

print(token.token_type, token.expires_in)
print(user.sub, user.preferred_username)
```

## 공개 API 개요

대표 공개 타입/함수:

- 설정: `CommonConfig`, `KeycloakConfig`, `PostgresConfig`, `SqliteConfig`, `ServiceConfigs`
- 설정 진입점: `CommonConfig`, `KeycloakConfig`, `LangfuseConfig`, `PostgresConfig`, `SqliteConfig`, `load_service_configs`
- 생성 함수: `create_keycloak_client`, `create_postgres_client`, `create_sqlite_client`, `create_nats_client`
- 런타임: `KeycloakAuthService`, `KeycloakProvisioner`, `check_all_services`, `close_service_clients`
- 에러: `ConfigError`, `ServiceClientError`, `ServiceClientWrapperError`

자세한 목록은 [docs/api.md](./docs/api.md)를 참고하세요.

## 설계 요약

- 서비스별 config를 직접 사용하는 경로를 우선 권장합니다.
- `load_service_configs()`가 서비스 묶음 로더의 기본 경로입니다.

- 서비스 생성은 `ServiceFactoryRegistry` 대신 `create_*_client()` 함수 중심입니다.
- `ServiceClientWrapper`는 `check()`/`close()`/민감정보 마스킹을 표준화합니다.
- NATS만 예외적으로 `NatsConnectionBuilder`를 반환하며 실제 연결은 비동기로 수행됩니다.
