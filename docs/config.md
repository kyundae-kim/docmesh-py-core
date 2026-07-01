# docmesh-py-core Configuration Guide

이 문서는 `docmesh-py-core`의 공개 환경변수 계약을 설명합니다.

목표는 세 가지입니다.

1. 어떤 값을 설정해야 하는지 빠르게 알 수 있게 하기
2. 필수 / 선택 / 조건부 필수 값을 구분하기
3. 공개 문서만으로도 통합 가능한 수준의 설정 가이드를 제공하기

## 1. 공통 원칙

- 모든 설정은 환경변수에서 읽습니다.
- 공백 문자열은 미설정으로 처리합니다.
- Boolean 값은 `true` / `false`로 해석합니다.
- 숫자형 값은 타입과 범위를 검증합니다.
- 민감정보는 Secret Manager 또는 배포 플랫폼의 secret 기능으로 주입하세요.
- 운영 환경에서는 TLS 검증을 기본 활성화하세요.
- 서비스별 timeout/retry는 공통 전역값이 아니라 각 서비스 환경변수로 관리합니다.
- 서비스별 config class(`CommonConfig`, `KeycloakConfig`, `LangfuseConfig`, `PostgresConfig`, `SqliteConfig` 등)를 직접 생성하면 aggregate `ServiceConfigs` 없이도 필요한 설정만 검증/로딩할 수 있습니다.
- `load_service_configs(services={...})`를 사용하면 필요한 서비스만 선택적으로 검증/로딩할 수 있습니다.


## 2. 공통 환경변수

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `DOCMESH_ENV` | 아니요 | `development` | 실행 환경 식별자 |
| `DOCMESH_HEALTHCHECK_ENABLED` | 아니요 | `true` | 헬스체크 활성화 여부 |
| `DOCMESH_LOG_LEVEL` | 아니요 | `INFO` | 공용 `configure_logging()` 기본 로그 레벨 |

권장값 예시:

- 로컬 개발: `DOCMESH_ENV=development`
- 통합 테스트: `DOCMESH_ENV=integration`
- 운영: `DOCMESH_ENV=production`

로깅 규칙:

- `configure_logging(level=...)`를 명시하지 않으면 `DOCMESH_LOG_LEVEL`을 읽습니다.
- `DOCMESH_LOG_LEVEL`이 없으면 기본값은 `INFO`입니다.
- 예: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- 잘못된 값이면 `ValueError`가 발생합니다.

## 3. 서비스별 설정

### 3.1 Keycloak

#### 기본 인증/JWT 검증

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK_URL` | 예 | 없음 | Keycloak 기본 URL |
| `KEYCLOAK_REALM` | 예 | 없음 | 인증 Realm |
| `KEYCLOAK_CLIENT_ID` | 예 | 없음 | OIDC Client ID |
| `KEYCLOAK_CLIENT_SECRET` | 조건부 | 없음 | Confidential Client 사용 시 secret |
| `KEYCLOAK_VERIFY_SSL` | 아니요 | `true` | TLS 인증서 검증 여부 |
| `KEYCLOAK_AUDIENCE` | 아니요 | 없음 | JWT 검증 대상 audience |
| `KEYCLOAK_REQUEST_TIMEOUT_SECONDS` | 아니요 | `10` | 요청 제한 시간 |
| `KEYCLOAK_MAX_RETRIES` | 아니요 | `3` | 최대 재시도 횟수 |
| `KEYCLOAK_JWKS_CACHE_TTL_SECONDS` | 아니요 | `300` | JWKS 캐시 TTL |

#### 토큰 획득

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK_TOKEN_GRANT_TYPE` | 아니요 | `client_credentials` | 토큰 grant type |
| `KEYCLOAK_TOKEN_SCOPE` | 아니요 | 없음 | 요청 scope |
| `KEYCLOAK_TOKEN_USERNAME` | 테스트용 선택값 | 없음 | 테스트 코드에서 password grant 호출 시 넘길 사용자명 |
| `KEYCLOAK_TOKEN_PASSWORD` | 테스트용 선택값 | 없음 | 테스트 코드에서 password grant 호출 시 넘길 비밀번호 |

규칙:

- 기본 grant는 `client_credentials`입니다.
- `password` grant를 쓰면 실제 `fetch_access_token(username=..., password=...)` 호출 시 사용자명/비밀번호가 필요합니다.
- 운영 애플리케이션은 username/password를 설정 객체에 고정하지 말고 호출 시점 인자로 전달하는 것을 권장합니다.
- 운영 환경 기본값으로 `password` grant를 두지 않는 것을 권장합니다.

#### 프로비저닝

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK_PROVISIONING_ENABLED` | 아니요 | `false` | 프로비저닝 활성화 여부 |
| `KEYCLOAK_PROVISIONING_DRY_RUN` | 아니요 | `false` | 변경 없이 계획만 출력 |
| `KEYCLOAK_ADMIN_REALM` | 조건부 | `master` | Admin API 인증 Realm |
| `KEYCLOAK_ADMIN_CLIENT_ID` | 조건부 | `admin-cli` | Admin API 인증 Client ID |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | 조건부 | 없음 | Service Account secret |
| `KEYCLOAK_ADMIN_USERNAME` | 조건부 | 없음 | 관리자 사용자명 |
| `KEYCLOAK_ADMIN_PASSWORD` | 조건부 | 없음 | 관리자 비밀번호 |
| `KEYCLOAK_REALM_ENABLED` | 아니요 | `true` | 대상 Realm 활성화 여부 |
| `KEYCLOAK_REALM_DISPLAY_NAME` | 아니요 | 없음 | Realm 표시 이름 |
| `KEYCLOAK_CLIENT_PUBLIC` | 아니요 | `false` | Client public 여부 |
| `KEYCLOAK_CLIENT_REDIRECT_URIS` | 아니요 | 없음 | 쉼표 구분 redirect URI 목록 |
| `KEYCLOAK_CLIENT_WEB_ORIGINS` | 아니요 | 없음 | 쉼표 구분 web origin 목록 |
| `KEYCLOAK_REALM_ROLES` | 아니요 | 없음 | 쉼표 구분 realm role 목록 |
| `KEYCLOAK_CLIENT_ROLES` | 아니요 | 없음 | 쉼표 구분 client role 목록 |

규칙:

- `KEYCLOAK_PROVISIONING_ENABLED=true`이면 Admin API 인증정보가 필요합니다.
- Service Account 방식 사용을 권장합니다.
- 선언에서 제거된 리소스는 자동 삭제하지 않습니다.

### 3.2 PostgreSQL

`POSTGRES_DSN`이 있으면 개별 필드보다 우선합니다.

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `POSTGRES_DSN` | 조건부 | 없음 | PostgreSQL 연결 URI |
| `POSTGRES_HOST` | 조건부 | 없음 | 호스트 |
| `POSTGRES_PORT` | 아니요 | `5432` | 포트 |
| `POSTGRES_DB` | 조건부 | 없음 | 데이터베이스 이름 |
| `POSTGRES_USER` | 조건부 | 없음 | 사용자명 |
| `POSTGRES_PASSWORD` | 조건부 | 없음 | 비밀번호 |
| `POSTGRES_SSLMODE` | 아니요 | `prefer` | SSL 모드 |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | 아니요 | `10` | 연결 제한 시간 |
| `POSTGRES_POOL_SIZE` | 아니요 | `5` | 기본 풀 크기 |
| `POSTGRES_MAX_OVERFLOW` | 아니요 | `10` | 추가 허용 연결 수 |

규칙:

- DSN을 쓰지 않으면 host/db/user/password 조합이 필요합니다.
- 기본 헬스체크는 `SELECT 1`입니다.

### 3.3 SQLite

SQLite는 로컬 개발, 단위 테스트, 경량 통합 테스트에 적합합니다.

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `SQLITE_PATH` | 조건부 | 없음 | 파일 경로 또는 `:memory:` |
| `SQLITE_READONLY` | 아니요 | `false` | 읽기 전용 모드 |
| `SQLITE_ENABLE_WAL` | 아니요 | `false` | WAL 활성화 여부 |
| `SQLITE_BUSY_TIMEOUT_MS` | 아니요 | `5000` | 잠금 대기 시간(ms) |

규칙:

- 상대경로는 애플리케이션 작업 디렉터리 기준으로 해석합니다.
- 파일이 없으면 생성 가능해야 합니다.
- 상위 디렉터리가 없으면 명확한 오류가 발생해야 합니다.
- 기본 헬스체크는 `SELECT 1`입니다.

### 3.4 MinIO

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `MINIO_ENDPOINT` | 예 | 없음 | `host:port` 형식 endpoint |
| `MINIO_ACCESS_KEY` | 예 | 없음 | access key |
| `MINIO_SECRET_KEY` | 예 | 없음 | secret key |
| `MINIO_SECURE` | 아니요 | `true` | HTTPS 사용 여부 |
| `MINIO_REGION` | 아니요 | 없음 | region |
| `MINIO_BUCKET` | 아니요 | 없음 | 기본 bucket |
| `MINIO_REQUEST_TIMEOUT_SECONDS` | 아니요 | `30` | 요청 제한 시간 |
| `MINIO_MAX_RETRIES` | 아니요 | `3` | 최대 재시도 횟수 |

기본 헬스체크는 `list_buckets()`입니다.

### 3.5 Milvus

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `MILVUS_URI` | 예 | 없음 | Milvus 서버 URI |
| `MILVUS_TOKEN` | 조건부 | 없음 | 인증 토큰 |
| `MILVUS_DB_NAME` | 아니요 | `default` | 데이터베이스 이름 |
| `MILVUS_COLLECTION` | 아니요 | 없음 | 기본 collection |
| `MILVUS_SECURE` | 아니요 | `false` | TLS 사용 여부 |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | 아니요 | `10` | 연결 제한 시간 |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | 아니요 | `30` | 요청 제한 시간 |
| `MILVUS_MAX_RETRIES` | 아니요 | `3` | 최대 재시도 횟수 |

기본 헬스체크는 `list_collections()`입니다.

### 3.6 Ollama

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `OLLAMA_HOST` | 예 | 없음 | Ollama API 기본 URL |
| `OLLAMA_GENERATION_MODEL` | 아니요 | 없음 | 기본 생성 모델 |
| `OLLAMA_EMBEDDING_MODEL` | 아니요 | 없음 | 기본 임베딩 모델 |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | 아니요 | `120` | 요청 제한 시간 |
| `OLLAMA_MAX_RETRIES` | 아니요 | `2` | 최대 재시도 횟수 |

기본 헬스체크는 `ps()`입니다.

### 3.7 Langfuse

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `LANGFUSE_ENABLED` | 아니요 | `true` | 활성화 여부 |
| `LANGFUSE_HOST` | 조건부 | 없음 | Langfuse API 기본 URL |
| `LANGFUSE_PUBLIC_KEY` | 조건부 | 없음 | public key |
| `LANGFUSE_SECRET_KEY` | 조건부 | 없음 | secret key |
| `LANGFUSE_RELEASE` | 아니요 | 없음 | 릴리스 식별자 |
| `LANGFUSE_ENVIRONMENT` | 아니요 | `DOCMESH_ENV` 값 | 환경 식별자 |
| `LANGFUSE_REQUEST_TIMEOUT_SECONDS` | 아니요 | `10` | 요청 제한 시간 |
| `LANGFUSE_MAX_RETRIES` | 아니요 | `3` | 최대 재시도 횟수 |

규칙:

- `LANGFUSE_ENABLED=false`이면 Langfuse를 선택 기능으로 비활성화할 수 있습니다.
- `LANGFUSE_ENABLED=true`일 때만 `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`가 필수입니다.
- 기본 헬스체크는 `auth_check()`입니다.

### 3.8 NATS

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `NATS_SERVERS` | 예 | 없음 | 쉼표 구분 서버 URL 목록 |
| `NATS_USER` | 조건부 | 없음 | 사용자명 인증 |
| `NATS_PASSWORD` | 조건부 | 없음 | 비밀번호 인증 |
| `NATS_TOKEN` | 조건부 | 없음 | 토큰 인증 |
| `NATS_CREDS_FILE` | 조건부 | 없음 | credentials 파일 경로 |
| `NATS_NAME` | 아니요 | `docmesh-py-core` | 연결 이름 |
| `NATS_CONNECT_TIMEOUT_SECONDS` | 아니요 | `10` | 연결 제한 시간 |
| `NATS_MAX_RECONNECT_ATTEMPTS` | 아니요 | `10` | 최대 재연결 횟수 |

규칙:

- 인증 방식은 user/password, token, creds file 중 하나를 선택합니다.
- `NATS_SERVERS`는 쉼표 구분 목록입니다.
- 헬스체크는 connect 후 `flush()` 확인입니다.

## 4. 최소 구성 가이드

이 절의 목적은 "각 서비스를 어떤 env 묶음으로 활성화하는가"를 빠르게 보여주는 것입니다.

### 4.1 서비스별 최소 활성화 세트

#### Keycloak 기본 인증 / 토큰 획득

필수:

- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `KEYCLOAK_CLIENT_SECRET` (`KEYCLOAK_CLIENT_PUBLIC=false`인 기본값 기준)

추가 조건:

- `KEYCLOAK_CLIENT_PUBLIC=true`면 `KEYCLOAK_CLIENT_SECRET` 없이도 설정 로딩 가능
- `KEYCLOAK_TOKEN_GRANT_TYPE=password`면 실제 token fetch 호출에서 `username`, `password` 함수 인자가 필요

#### PostgreSQL 저장소

둘 중 하나를 선택합니다.

1. DSN 방식
   - `POSTGRES_DSN`
2. 개별 필드 방식
   - `POSTGRES_HOST`
   - `POSTGRES_DB`
   - `POSTGRES_USER`
   - `POSTGRES_PASSWORD`

선택 항목:

- `POSTGRES_PORT`
- `POSTGRES_SSLMODE`
- `POSTGRES_CONNECT_TIMEOUT_SECONDS`
- `POSTGRES_POOL_SIZE`
- `POSTGRES_MAX_OVERFLOW`

#### SQLite 저장소

필수:

- `SQLITE_PATH`

선택 항목:

- `SQLITE_READONLY`
- `SQLITE_ENABLE_WAL`
- `SQLITE_BUSY_TIMEOUT_MS`

#### Langfuse 비활성화

최소:

- `LANGFUSE_ENABLED=false`

이 경우 아래 값들은 생략 가능합니다.

- `LANGFUSE_HOST`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`

#### Langfuse 활성화

필수:

- `LANGFUSE_ENABLED=true` (기본값)
- `LANGFUSE_HOST`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`

#### NATS 인증 모드

필수:

- `NATS_SERVERS`

아래 세 모드 중 **하나만** 선택합니다.

1. user/password
   - `NATS_USER`
   - `NATS_PASSWORD`
2. token
   - `NATS_TOKEN`
3. creds file
   - `NATS_CREDS_FILE`

### 4.2 최소 설정 예시

#### PostgreSQL 기반 예시

```env
DOCMESH_ENV=development
DOCMESH_HEALTHCHECK_ENABLED=true

KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=docmesh-backend
KEYCLOAK_CLIENT_SECRET=replace-me

POSTGRES_HOST=postgres.example.com
POSTGRES_PORT=5432
POSTGRES_DB=docmesh
POSTGRES_USER=docmesh
POSTGRES_PASSWORD=replace-me

MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=replace-me
MINIO_SECRET_KEY=replace-me

MILVUS_URI=http://milvus.example.com:19530
OLLAMA_HOST=http://ollama.example.com:11434
LANGFUSE_HOST=https://langfuse.example.com
LANGFUSE_PUBLIC_KEY=replace-me
LANGFUSE_SECRET_KEY=replace-me
NATS_SERVERS=nats://n1.example.com:4222
```

#### SQLite 기반 예시

```env
DOCMESH_ENV=development
DOCMESH_HEALTHCHECK_ENABLED=true

KEYCLOAK_URL=https://keycloak.example.com
KEYCLOAK_REALM=docmesh
KEYCLOAK_CLIENT_ID=docmesh-backend
KEYCLOAK_CLIENT_SECRET=replace-me

SQLITE_PATH=./data/docmesh.sqlite3
SQLITE_READONLY=false
SQLITE_ENABLE_WAL=true
SQLITE_BUSY_TIMEOUT_MS=5000

MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=replace-me
MINIO_SECRET_KEY=replace-me

MILVUS_URI=http://milvus.example.com:19530
OLLAMA_HOST=http://ollama.example.com:11434
LANGFUSE_HOST=https://langfuse.example.com
LANGFUSE_PUBLIC_KEY=replace-me
LANGFUSE_SECRET_KEY=replace-me
NATS_SERVERS=nats://n1.example.com:4222
```

## 5. 보안 운영 가이드

- 실제 secret 값이 들어간 `.env` 파일은 버전 관리에 포함하지 마세요.
- 비밀번호, token, secret, 전체 DSN/URI를 로그에 그대로 남기지 마세요.
- 운영 환경에서는 TLS 검증 비활성화를 기본값으로 두지 마세요.
- Keycloak 프로비저닝은 가능하면 최소 권한 Service Account로 수행하세요.
- Access Token, Refresh Token 원문은 애플리케이션 로그나 트레이싱 이벤트에 기록하지 마세요.

## 6. 자주 실패하는 설정 패턴 / 트러블슈팅

### `ConfigError: Missing required environment variable ...`

의미:

- 필수 env가 비어 있거나 누락되었습니다.
- 이 라이브러리는 공백 문자열도 미설정으로 취급합니다.

확인할 것:

- 값이 정말 export 되었는지
- 빈 문자열(`""`, 공백만 있는 값)로 주입된 것은 아닌지
- conditional 필수 규칙을 놓친 것은 아닌지

### `KEYCLOAK_CLIENT_SECRET` 누락 오류

원인:

- 기본값은 confidential client 전제이므로 `KEYCLOAK_CLIENT_SECRET`가 필요합니다.

해결:

- confidential client면 secret 제공
- public client면 `KEYCLOAK_CLIENT_PUBLIC=true` 명시

### `KEYCLOAK provisioning requires a single admin auth mode`

원인:

- service account 방식과 username/password 방식을 동시에 주었거나, 둘 다 주지 않았습니다.

해결:

- 아래 둘 중 하나만 선택
  - `KEYCLOAK_ADMIN_CLIENT_SECRET`
  - `KEYCLOAK_ADMIN_USERNAME` + `KEYCLOAK_ADMIN_PASSWORD`

### `NATS requires a single authentication mode`

원인:

- `NATS_USER/NATS_PASSWORD`, `NATS_TOKEN`, `NATS_CREDS_FILE`를 중복 지정했습니다.

해결:

- 인증 모드를 하나만 남기세요.

### `NATS_USER and NATS_PASSWORD must be provided together`

원인:

- user/password 모드에서 둘 중 하나만 설정했습니다.

해결:

- 둘 다 제공하거나, 다른 인증 모드로 전환하세요.

### production 환경 SSL 제약

의미:

- `DOCMESH_ENV`가 `production` 또는 `prod`면 보안 검증이 추가됩니다.

제약:

- `KEYCLOAK_VERIFY_SSL=false` 불가
- `MINIO_SECURE=false` 불가
- `MILVUS_SECURE=false` 불가

문제 발생 시:

- 운영 환경 식별자가 맞는지 확인
- TLS 사용/인증서 검증 설정을 다시 확인

## 7. 개발자용 빠른 점검 체크리스트

- Keycloak: URL / realm / client_id / secret(or public client) 준비됐는가?
- Postgres: DSN 또는 host/db/user/password 조합이 완성됐는가?
- SQLite: `SQLITE_PATH`가 실제 앱 작업 디렉터리 기준으로 유효한가?
- Langfuse: disabled인지, enabled면 3개 key가 모두 있는가?
- NATS: 인증 모드를 하나만 선택했는가?
- production이면 TLS 검증 비활성화 값이 숨어 있지 않은가?

## 8. 문서 연계

- 사용 흐름: [README](../README.md)
- 공개 API: [api.md](./api.md)
- 실제 통합 예시: [examples.md](./examples.md)
- 요구사항 기준: [srs.md](./srs.md)
- 테스트 전략: [test.md](./test.md)
