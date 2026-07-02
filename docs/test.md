# docmesh-py-core 테스트 가이드

이 문서는 현재 코드와 테스트 스위트(`test_docmesh_py_core`)를 기준으로 유지되는 테스트 전략 문서입니다.

핵심 목표는 다음과 같습니다.

- 환경변수 기반 설정 검증 보장
- 서비스별 클라이언트 생성 계약 보장
- `health check` / `ping` / `check` 인터페이스 검증
- 예외와 로그에서 민감정보 비노출 보장
- Keycloak 프로비저닝, 토큰 획득, JWT 검증 회귀 방지
- 로깅/재시도/관측성 helper 계약 유지

---

## 테스트 원칙

### 테스트 계층

1. **단위 테스트**
   - 위치: `./test_docmesh_py_core`
   - mock/stub 중심
   - 외부 네트워크 연결 없이 수행
   - 설정 파싱, 검증, 마스킹, builder 인자 매핑, health wrapper, 로깅/재시도 helper 검증

2. **통합 테스트**
   - 실제 SDK 또는 테스트 서비스 사용
   - PostgreSQL, MinIO, Milvus, NATS, Keycloak, Ollama, Langfuse 대상
   - `DOCMESH_ENV=integration`일 때만 실행

3. **보안/회귀 테스트**
   - 민감정보 노출 방지 검증
   - Keycloak 인증 실패/일시적 오류 마스킹 검증
   - JWT 검증 오류 회귀 방지

### 기본 방침

- 새 기능은 가능하면 단위 테스트를 먼저 추가합니다.
- 외부 서비스 SDK 호출은 mock으로 계약 위주 검증을 우선합니다.
- 네트워크, 인증, 시간 의존 로직은 deterministic fixture 또는 주입 가능한 clock/sleep으로 고정합니다.
- 토큰, 비밀번호, secret 값은 테스트 데이터라도 마스킹 검증 대상에 포함합니다.
- 저장소 루트에서는 기본 `pytest` 대신 `uv run pytest`를 표준 실행 계약으로 사용합니다.

### integration 테스트 방침

- integration 테스트는 실제 네트워크, 실제 SDK, 테스트 컨테이너 또는 별도 테스트용 서비스에 연결합니다.
- 실행 조건은 별도 플래그가 아니라 `DOCMESH_ENV=integration` 같은 실행 환경 식별자를 기준으로 합니다.
- `test_docmesh_py_core/conftest.py`의 integration helper는 `env/integration.env`와 프로세스 환경을 조합해 전용 `*IntegrationConfig`를 생성합니다.
- service별 integration 테스트는 일반 `load_service_configs()` 전체 로더보다 서비스별 integration config class를 직접 사용하는 경로를 우선합니다.
- 실패 원인 분석을 위해 endpoint, marker, 환경 구분은 남기되 secret/token/password는 남기지 않습니다.

---

## 테스트 범위

### 설정 로더 / 설정 모델

검증 대상:

- 필수 환경변수 누락 감지
- 공백 문자열을 누락으로 처리
- bool 파싱 (`true` / `false`, 대소문자 무시)
- 정수형 필드 파싱 및 범위 검증
- 조건부 필수값 검증
- 서비스별 상호 배타 조건 검증
- 기본값 적용
- 비활성화 기능의 optional field 완화
- `load_service_configs()`의 `ConfigError` 래핑 동작

대표 시나리오:

- `KEYCLOAK_URL` 누락 시 설정 오류 발생
- `POSTGRES_DSN`이 있으면 host/user/password 조합보다 우선
- `LANGFUSE_ENABLED=false`일 때 Langfuse key 미입력 허용
- `NATS_USER/NATS_PASSWORD`, `NATS_TOKEN`, `NATS_CREDS_FILE` 동시 설정 시 오류
- `KEYCLOAK_TOKEN_GRANT_TYPE=password`는 설정 로딩 시 허용되며, 실제 호출에서 함수 인자 username/password가 필요
- `KEYCLOAK_CLIENT_PUBLIC=true`이면 client secret 선택 허용
- timeout/pool 크기 범위 검증

권장 테스트 파일:

- `test_docmesh_py_core/test_config.py`
- `test_docmesh_py_core/test_env_example.py`

### 서비스 factory / builder

검증 대상:

- 서비스별 factory가 올바른 SDK 생성자를 호출하는지
- 필요한 서비스만 선택 로딩 가능한지
- builder 결과가 `ping()` / `check()` / `close()` 계약을 따르는지
- 종료가 필요한 client가 적절히 정리되는지
- NATS처럼 비동기 연결 서비스가 event loop를 임의 생성/종료하지 않는지

현재 구현의 중요한 사실:

- PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, Keycloak factory는 클라이언트를 즉시 생성합니다.
- NATS만 `NatsConnectionBuilder`를 반환하고 실제 연결을 지연시킵니다.
- `ServiceClientWrapper.check()` 실패는 `ServiceClientWrapperError`로 표준화됩니다.

대표 시나리오:

- Keycloak factory가 `KeycloakAuthService(settings)` 생성
- PostgreSQL factory가 `create_engine()`에 pool/timeout/sslmode 전달
- SQLite factory가 `readonly`, `busy_timeout_ms`, `enable_wal` 반영
- MinIO factory가 endpoint/access_key/secret_key/secure/cert_check 전달
- Milvus factory가 uri/token/db_name/request timeout 전달
- Ollama factory가 host/timeout 전달
- Langfuse factory가 enabled=false면 `None` 반환
- NATS builder가 connect kwargs만 보유하고 실제 연결은 `connect()`/`ping()`/`check()` 시 수행

권장 테스트 파일:

- `test_docmesh_py_core/test_factories.py`

### health check 집계

검증 대상:

- 서비스별 check 함수 실행
- 응답 시간 측정
- 실패 시 서비스명/오류 보존
- 오류 메시지 내 민감정보 마스킹
- required service 실패 시 `HealthCheckError` 발생
- optional service 실패 시 결과만 실패로 표시
- `parallel=True`일 때 병렬 실행되더라도 입력 순서대로 결과 반환

권장 테스트 파일:

- `test_docmesh_py_core/test_health.py`

### 관측성 / 로깅 / 재시도

검증 대상:

- `build_service_log_event()`의 표준 필드 구성
- 민감한 error/extra 필드 마스킹
- `retry_call()`의 지수 백오프
- `KeycloakAuthService.fetch_access_token()` 재시도 이벤트 로깅
- `configure_logging()`의 파일 출력 및 `DOCMESH_LOG_LEVEL` 해석
- `log_function_boundary()`의 시작/종료 로그 기록

권장 테스트 파일:

- `test_docmesh_py_core/test_observability.py`

### 민감정보 마스킹 / 보안

검증 대상:

- DSN/URI의 사용자명, 비밀번호, 토큰, query parameter 마스킹
- 예외 메시지 마스킹
- 로그에 access token / refresh token / client secret 미노출
- JWT raw string 미노출

권장 테스트 파일:

- `test_docmesh_py_core/test_security.py`
- `test_docmesh_py_core/test_keycloak.py`

### Keycloak 프로비저닝

검증 대상:

- realm/client/role 생성 및 갱신 판단
- 동일 입력 반복 시 멱등성 보장
- dry-run 시 실제 변경 없음
- 삭제 비수행 정책 유지
- 부분 실패 시 성공/실패 항목 구분
- 관리자 인증 방식 분기 처리

권장 테스트 파일:

- `test_docmesh_py_core/test_keycloak_provisioning.py`

### Keycloak 토큰 획득 / JWT 검증

검증 대상:

- client credentials grant
- password grant
- optional scope 전달
- 정상 응답 매핑
- 인증 실패 / 설정 오류 / 일시적 HTTP 오류 분류
- 민감정보 비노출
- HS256 / RS256 검증
- JWKS TTL 및 key rotation 처리
- issuer/audience/expiry/nbf 검증
- realm/client roles 분리 추출

권장 테스트 파일:

- `test_docmesh_py_core/test_keycloak.py`

---

## 통합 테스트 범위

다음 항목은 단위 테스트와 분리해 운영합니다.

- Keycloak discovery / token / provisioning smoke test
- PostgreSQL `SELECT 1` 실제 수행
- SQLite `SELECT 1` 실제 수행
- MinIO `list_buckets()` 실제 수행
- Milvus `list_collections()` 실제 수행
- Ollama `ps()` 실제 수행
- Langfuse `auth_check()` 실제 수행
- NATS connect + flush 실제 수행

### 실행 환경 구성

- 로컬 실행은 `env/integration.env`를 우선 기준으로 삼고, 프로세스 환경변수가 이를 덮을 수 있습니다.
- integration helper는 `DOCMESH_ENV=integration`이 아니면 테스트를 skip 합니다.
- 테스트 데이터는 운영 계정이 아닌 전용 realm, bucket, database, client, token으로 분리합니다.

예시:

```bash
uv run pytest -q -m "not integration"
DOCMESH_ENV=integration uv run pytest -q -m integration
DOCMESH_ENV=integration uv run pytest -q test_docmesh_py_core/test_integration_services.py
```

---

## pytest 마커

등록된 마커:

- `unit`
- `integration`
- `security`
- `keycloak`
- `health`

이 마커들은 `pyproject.toml`의 `[tool.pytest.ini_options.markers]`와 동기화되어야 합니다.

---

## 예시 테스트 구조

```text
test_docmesh_py_core/
├── conftest.py
├── test_config.py
├── test_env_example.py
├── test_factories.py
├── test_health.py
├── test_keycloak.py
├── test_keycloak_provisioning.py
├── test_observability.py
├── test_project_contract.py
└── test_security.py
```

---

## 최소 체크리스트

릴리스 전 최소한 아래 테스트는 모두 녹색이어야 합니다.

- [ ] 설정 모델 기본값 테스트
- [ ] 필수 env 누락/조건부 필수 조합 테스트
- [ ] 모든 서비스 factory 인자 매핑 테스트
- [ ] `ServiceClientWrapper` 오류 표준화 테스트
- [ ] health 집계 성공/실패/병렬 실행 테스트
- [ ] 민감정보 마스킹 테스트
- [ ] Keycloak token grant 테스트
- [ ] JWT 검증 성공/실패 테스트
- [ ] JWKS TTL/rotation 테스트
- [ ] `.env.example`와 설정 모델 동기화 테스트
- [ ] `configure_logging` / `retry_call` / `build_service_log_event` 테스트

---

## 권장 실행 명령

```bash
uv run pytest -q test_docmesh_py_core
uv run pytest -q test_docmesh_py_core/test_factories.py
uv run pytest -q test_docmesh_py_core/test_keycloak.py
uv run pytest -q -m "not integration"
DOCMESH_ENV=integration uv run pytest -q -m integration
```

---

## 문서 유지 원칙

다음 변경 시 이 문서를 함께 갱신합니다.

- 신규 외부 서비스 추가
- 환경변수 스키마 변경
- health check 방식 변경
- Keycloak provisioning/token/JWT 계약 변경
- 로깅/재시도/관측성 helper 계약 변경
- integration helper / 실행 게이트 변경
