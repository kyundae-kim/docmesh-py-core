---
title: 설정 시스템 (pydantic-settings)
created: 2026-06-10
updated: 2026-06-11
type: concept
tags: [configuration, sdk-design, python]
sources: [raw/articles/prd.md, raw/project-docs/config.md, raw/project-docs/api.md, raw/project-docs/sdk.md]
confidence: high
---

# 설정 시스템 (pydantic-settings)

`config.py`는 pydantic-settings를 사용해 환경 변수를 타입-안전하게 읽고 검증한다.
애플리케이션 시작 시 **한 번만** 로드해 전체 수명주기 동안 재사용한다.

## 공통 원칙 ^[raw/articles/prd.md]

- 모든 설정은 환경변수에서 읽는다. 코드에 URL·계정·비밀번호·토큰·secret key를 하드코딩하지 않는다.
- 공백 문자열은 값이 없는 것으로 간주한다.
- boolean 값은 대소문자 무관하게 `true` / `false`로 해석한다.
- 숫자형 값은 허용 범위를 검증한다.
- **공통 timeout/retry는 없다** — 서비스별 환경변수로만 관리한다.

## 진입점

```python
from docmesh_py_core import load_settings
import os

settings = load_settings(os.environ)   # Mapping[str, str] 수용
```

`load_settings`는 내부적으로 `Settings(**env_dict)` 를 호출하고
pydantic ValidationError를 `ConfigError`로 래핑해 반환한다.

## Settings 집계 모델

```python
class Settings(BaseSettings):
    env: str = "development"                   # DOCMESH_ENV
    healthcheck_enabled: bool = True           # DOCMESH_HEALTHCHECK_ENABLED

    keycloak: KeycloakConfig
    postgres: PostgresConfig | None
    sqlite: SqliteConfig | None
    minio: MinioConfig
    milvus: MilvusConfig
    ollama: OllamaConfig
    langfuse: LangfuseConfig
    nats: NatsConfig
```

## 공통 환경변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `DOCMESH_ENV` | - | `development` | 실행 환경 식별자 |
| `DOCMESH_HEALTHCHECK_ENABLED` | - | `true` | 헬스체크 활성화 여부 |

## 서비스별 환경변수

### Keycloak (`KEYCLOAK_`)

#### 기본 인증

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `KEYCLOAK_URL` | ✅ | - | Keycloak 기본 URL |
| `KEYCLOAK_REALM` | ✅ | - | 인증 Realm |
| `KEYCLOAK_CLIENT_ID` | ✅ | - | OIDC Client ID |
| `KEYCLOAK_CLIENT_SECRET` | 조건부 | - | Confidential Client Secret |
| `KEYCLOAK_VERIFY_SSL` | - | `true` | TLS 인증서 검증 여부 |
| `KEYCLOAK_AUDIENCE` | - | - | JWT 검증 대상 Audience |
| `KEYCLOAK_REQUEST_TIMEOUT_SECONDS` | - | `10` | OIDC/JWKS 요청 제한 시간 |
| `KEYCLOAK_MAX_RETRIES` | - | `3` | 일시적 HTTP 오류 최대 재시도 횟수 |

#### 토큰 획득

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `KEYCLOAK_TOKEN_GRANT_TYPE` | - | `client_credentials` | 토큰 획득 grant type |
| `KEYCLOAK_TOKEN_SCOPE` | - | - | 토큰 요청 scope |
| `KEYCLOAK_TOKEN_USERNAME` | 조건부 | - | password grant 사용자명 |
| `KEYCLOAK_TOKEN_PASSWORD` | 조건부 | - | password grant 비밀번호 |

#### 프로비저닝

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `KEYCLOAK_PROVISIONING_ENABLED` | - | `false` | 프로비저닝 활성화 여부 |
| `KEYCLOAK_PROVISIONING_DRY_RUN` | - | `false` | 변경 없이 계획만 출력 |
| `KEYCLOAK_ADMIN_REALM` | 조건부 | `master` | Admin API 인증 Realm |
| `KEYCLOAK_ADMIN_CLIENT_ID` | 조건부 | `admin-cli` | Admin API 인증 Client ID |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | 조건부 | - | Service Account Secret |
| `KEYCLOAK_ADMIN_USERNAME` | 조건부 | - | 관리자 사용자명 |
| `KEYCLOAK_ADMIN_PASSWORD` | 조건부 | - | 관리자 비밀번호 |
| `KEYCLOAK_REALM_ENABLED` | - | `true` | 대상 Realm 활성화 여부 |
| `KEYCLOAK_REALM_DISPLAY_NAME` | - | - | 대상 Realm 표시 이름 |
| `KEYCLOAK_CLIENT_PUBLIC` | - | `false` | 생성할 Client의 Public 여부 |
| `KEYCLOAK_CLIENT_REDIRECT_URIS` | - | - | 쉼표 구분 Redirect URI 목록 |
| `KEYCLOAK_CLIENT_WEB_ORIGINS` | - | - | 쉼표 구분 Web Origin 목록 |
| `KEYCLOAK_REALM_ROLES` | - | - | 쉼표 구분 Realm Role 목록 |
| `KEYCLOAK_CLIENT_ROLES` | - | - | 쉼표 구분 Client Role 목록 |

**프로비저닝 조건부 필수**: `KEYCLOAK_PROVISIONING_ENABLED=true`이면 Admin API 인증정보 필요.
인증 방식은 **service account** 또는 **관리자 사용자명/비밀번호** 중 하나만.

**password grant 조건부 필수**: `KEYCLOAK_TOKEN_GRANT_TYPE=password`이면
`KEYCLOAK_TOKEN_USERNAME` + `KEYCLOAK_TOKEN_PASSWORD` 필요.

### PostgreSQL (`POSTGRES_`)

`POSTGRES_DSN` 설정 시 개별 변수보다 우선.

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `POSTGRES_DSN` | 조건부 | - | 연결 URI |
| `POSTGRES_HOST` | 조건부 | - | 데이터베이스 호스트 |
| `POSTGRES_PORT` | - | `5432` | 포트 |
| `POSTGRES_DB` | 조건부 | - | 데이터베이스 이름 |
| `POSTGRES_USER` | 조건부 | - | 사용자명 |
| `POSTGRES_PASSWORD` | 조건부 | - | 비밀번호 |
| `POSTGRES_SSLMODE` | - | `prefer` | SSL 모드 |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | - | `10` | 연결 제한 시간 |
| `POSTGRES_POOL_SIZE` | - | `5` | 커넥션 풀 크기 |
| `POSTGRES_MAX_OVERFLOW` | - | `10` | 최대 초과 연결 수 |

### SQLite (`SQLITE_`)

SQLite는 PostgreSQL과 별도 설정 집합으로 관리되며, `SQLITE_*` 환경변수가 존재할 때만 선택적으로 활성화된다.^[raw/project-docs/config.md]

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `SQLITE_PATH` | 조건부 | - | SQLite 파일 경로 또는 `:memory:` |
| `SQLITE_READONLY` | - | `false` | 읽기 전용 모드 |
| `SQLITE_ENABLE_WAL` | - | `false` | WAL 모드 활성화 |
| `SQLITE_BUSY_TIMEOUT_MS` | - | `5000` | 잠금 대기 시간(ms) |

규칙:

- `SQLITE_PATH=:memory:`는 프로세스 내 메모리 DB를 의미한다.
- 명시적 backend selector 없이, 소비 프로젝트가 `settings.sqlite is not None` 여부로 분기한다.
- health check는 `SELECT 1`을 사용한다.

### MinIO (`MINIO_`)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `MINIO_ENDPOINT` | ✅ | - | `host:port` 형식 endpoint |
| `MINIO_ACCESS_KEY` | ✅ | - | Access Key |
| `MINIO_SECRET_KEY` | ✅ | - | Secret Key |
| `MINIO_SECURE` | - | `true` | HTTPS 사용 여부 |
| `MINIO_REGION` | - | - | 리전 |
| `MINIO_BUCKET` | - | - | 기본 Bucket |
| `MINIO_REQUEST_TIMEOUT_SECONDS` | - | `30` | 요청 제한 시간 |
| `MINIO_MAX_RETRIES` | - | `3` | 일시적 요청 오류 최대 재시도 횟수 |

> Production에서 `MINIO_SECURE=false`는 `ConfigError` 발생.

### Milvus (`MILVUS_`)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `MILVUS_URI` | ✅ | - | 연결 URI |
| `MILVUS_TOKEN` | 조건부 | - | 인증 토큰 |
| `MILVUS_DB_NAME` | - | `default` | 데이터베이스 이름 |
| `MILVUS_COLLECTION` | - | - | 기본 Collection |
| `MILVUS_SECURE` | - | `false` | TLS 사용 여부 |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | - | `10` | 연결 제한 시간 |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | - | `30` | 요청 제한 시간 |
| `MILVUS_MAX_RETRIES` | - | `3` | 일시적 연결/요청 오류 최대 재시도 횟수 |

> Production에서 `MILVUS_SECURE=false`는 `ConfigError` 발생.

### Ollama (`OLLAMA_`)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `OLLAMA_HOST` | ✅ | - | Ollama API 기본 URL |
| `OLLAMA_GENERATION_MODEL` | - | - | 텍스트 생성 모델명 |
| `OLLAMA_EMBEDDING_MODEL` | - | - | 임베딩 모델명 |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | - | `120` | 요청 제한 시간 (생성 호출이 오래 걸림) |
| `OLLAMA_MAX_RETRIES` | - | `2` | 일시적 HTTP 오류 최대 재시도 횟수 |

### Langfuse (`LANGFUSE_`)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `LANGFUSE_ENABLED` | - | `true` | 활성화 여부 |
| `LANGFUSE_HOST` | enabled일 때 ✅ | - | 서버 URL |
| `LANGFUSE_PUBLIC_KEY` | enabled일 때 ✅ | - | 공개 키 |
| `LANGFUSE_SECRET_KEY` | enabled일 때 ✅ | - | 시크릿 키 |
| `LANGFUSE_ENVIRONMENT` | - | `DOCMESH_ENV` 값 | Langfuse 환경 식별자 |
| `LANGFUSE_RELEASE` | - | - | 릴리즈 버전 태그 |
| `LANGFUSE_REQUEST_TIMEOUT_SECONDS` | - | `10` | API 요청 제한 시간 |
| `LANGFUSE_MAX_RETRIES` | - | `3` | 일시적 전송 오류 최대 재시도 횟수 |

### NATS (`NATS_`)

인증 방식은 아래 중 하나만 선택 (동시 설정 시 `ConfigError`):

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `NATS_SERVERS` | ✅ | - | 쉼표 구분 서버 URL 목록 |
| `NATS_USER` | 조건부 | - | 사용자명 인증 — 사용자명 |
| `NATS_PASSWORD` | 조건부 | - | 사용자명 인증 — 비밀번호 (USER와 쌍 필수) |
| `NATS_TOKEN` | 조건부 | - | 토큰 인증 |
| `NATS_CREDS_FILE` | 조건부 | - | Credentials 파일 경로 |
| `NATS_NAME` | - | `docmesh-py-core` | 연결 식별자 |
| `NATS_CONNECT_TIMEOUT_SECONDS` | - | `10` | 연결 제한 시간 |
| `NATS_MAX_RECONNECT_ATTEMPTS` | - | `10` | 최대 재연결 횟수 |

## 교차 검증 규칙 (ConfigError 발생 조건)

| 조건 | 오류 |
|------|------|
| Production + `MINIO_SECURE=false` | MinIO는 production에서 HTTPS 필수 |
| Production + `MILVUS_SECURE=false` | Milvus는 production에서 TLS 필수 |
| `LANGFUSE_ENABLED=true` + key 미설정 | Langfuse 활성화 시 HOST/PUBLIC_KEY/SECRET_KEY 필수 |
| `POSTGRES_DSN` 없음 + HOST/DB/USER/PASSWORD 중 누락 | PostgreSQL 연결 정보 불충분 |
| `SQLITE_PATH` 없음 + SQLite 사용을 기대하는 코드 경로 진입 | SQLite 연결 정보 불충분 |
| `NATS_USER/PASSWORD` + `NATS_TOKEN` 동시 설정 | NATS 인증 방식은 하나만 선택 |
| `KEYCLOAK_PROVISIONING_ENABLED=true` + Admin 인증정보 없음 | 프로비저닝에 Admin 인증정보 필요 |
| `KEYCLOAK_TOKEN_GRANT_TYPE=password` + username/password 없음 | password grant 자격증명 필요 |

## 환경별 운영 규칙 ^[raw/project-docs/config.md]

- 로컬/개발/스테이징/운영은 코드가 아니라 환경변수로 구분한다.
- 운영에서는 TLS와 인증서 검증을 기본값으로 유지한다.
- integration 테스트는 운영 설정과 분리된 별도 환경변수 세트를 사용한다.

## 검증 체크리스트

설정 추가/변경 시:
- [ ] 필수 여부가 문서(`docs/config.md`)와 코드에서 일치하는가
- [ ] 기본값이 문서와 코드에서 일치하는가
- [ ] 민감정보 항목이 마스킹 정책 대상에 포함되는가
- [ ] `.env.example`와 문서가 동기화되어 있는가
- [ ] 테스트가 새 설정 항목을 검증하는가

## 관련 개념

- [[docmesh-sdk-overview]] — SDK 전체 구조
- [[service-factory-registry]] — Settings를 소비해 클라이언트 생성
- [[sensitive-value-masking]] — 에러 메시지 마스킹
- [[keycloak-auth-flow]] — KeycloakConfig 상세
- [[test-strategy]] — 설정 유닛 테스트 패턴
