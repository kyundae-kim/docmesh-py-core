# docmesh-py-core 테스트 가이드

## 개요

이 문서는 `docs/prd.md`를 기준으로 `docmesh-py-core`에서 검증해야 하는
테스트 범위, 전략, 우선순위를 정리한다.

핵심 목표는 다음과 같다.

- 환경변수 기반 설정 검증 보장
- 서비스별 클라이언트 생성 계약 보장
- `health check` / `ping` / `check` 인터페이스 검증
- 예외와 로그에서 민감정보 비노출 보장
- Keycloak 프로비저닝, 토큰 획득, JWT 검증 회귀 방지

---

## 테스트 원칙

### 테스트 계층

1. **단위 테스트**
   - 위치: `./test_docmesh_py_core`
   - mock/stub 중심
   - 외부 네트워크 연결 없이 수행
   - 설정 파싱, 검증, 마스킹, builder 인자 매핑, health wrapper 검증

2. **통합 테스트**
   - 실제 SDK 또는 테스트 컨테이너 사용
   - PostgreSQL, MinIO, Milvus, NATS, Keycloak, Ollama, Langfuse 대상
   - CI에서는 별도 job 또는 선택 실행 권장

3. **보안/회귀 테스트**
   - 민감정보 노출 방지 검증
   - 잘못된 토큰, 서명 오류, audience mismatch, timeout/connection error 분류 검증

### 기본 방침

- 새 기능은 가능하면 단위 테스트를 먼저 추가한다.
- 외부 서비스 SDK 호출은 mock으로 계약 위주 검증을 우선한다.
- 네트워크, 인증, 시간 의존 로직은 deterministic fixture로 고정한다.
- 토큰, 비밀번호, secret 값은 테스트 데이터라도 마스킹 검증 대상에 포함한다.
- 저장소 루트에서는 기본 `pytest` 대신 `uv run pytest`를 표준 실행 계약으로 사용한다.
  프로젝트 가상환경의 의존성과 pytest 설정을 일관되게 적용하기 위해서다.

### integration 테스트 방침

- integration 테스트는 실제 네트워크, 실제 SDK, 테스트 컨테이너 또는 별도 테스트용 서비스에 연결한다.
- 실행 조건은 별도 플래그가 아니라 `DOCMESH_ENV=integration` 같은 실행 환경 식별자를 기준으로 한다.
- 단위 테스트와 동일한 시나리오를 반복하기보다, 실제 연결 가능 여부와 주요 실패 분류를 검증한다.
- 기본 CI에서는 `unit`과 분리해 실행하고, 필요 시 브랜치/야간/릴리스 파이프라인에서만 활성화한다.
- 실패 원인 분석을 위해 서비스 endpoint, 테스트 대상 환경, 사용한 marker를 로그에 남기되 secret/token/password는 제외한다.
- flaky 방지를 위해 timeout, 재시도, readiness 대기 조건을 명시한다.

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

대표 시나리오:

- `KEYCLOAK_URL` 누락 시 설정 오류 발생
- `POSTGRES_DSN`이 있으면 host/user/password 조합보다 우선
- `LANGFUSE_ENABLED=false`일 때 Langfuse key 미입력 허용
- `NATS_USER/NATS_PASSWORD`, `NATS_TOKEN`, `NATS_CREDS_FILE` 동시 설정 시 오류
- `KEYCLOAK_TOKEN_GRANT_TYPE=password`일 때 username/password 필수
- `KEYCLOAK_CLIENT_PUBLIC=true`이면 client secret 선택 허용
- timeout/retry 값이 음수 또는 0일 때 오류

권장 테스트 파일:

- `test_docmesh_py_core/test_config.py`
- `test_docmesh_py_core/test_env_example.py`

### 서비스 factory / builder

검증 대상:

- 서비스별 builder가 올바른 SDK 생성자를 호출하는지
- 필요한 서비스만 lazy create 되는지
- builder 결과가 `ping()` / `check()` / `close()` 계약을 따르는지
- 종료가 필요한 client가 적절히 정리되는지
- NATS처럼 비동기 연결 서비스가 event loop를 임의 생성/종료하지 않는지

대표 시나리오:

- Keycloak builder가 `KeycloakAuthService(settings)` 생성
- PostgreSQL builder가 `create_engine()`에 pool/timeout/sslmode 전달
- MinIO builder가 endpoint/access_key/secret_key/secure 전달
- Milvus builder가 uri/token/db_name/timeout 전달
- Ollama builder가 host/timeout 전달
- Langfuse builder가 enabled=false면 `None` 반환
- NATS builder가 connect kwargs만 보유하고 실제 연결은 `connect()`/`ping()` 시 수행
- 각 wrapper의 `check()`가 서비스별 health call을 수행

권장 테스트 파일:

- `test_docmesh_py_core/test_factories.py`

### health check 집계

검증 대상:

- 서비스별 check 함수 실행
- 응답 시간 측정
- 실패 시 서비스명/오류 보존
- 오류 메시지 내 민감정보 마스킹
- required service 실패 시 집계 예외 발생
- optional service 실패 시 상태 결과만 실패로 표시
- `parallel=True`일 때 병렬 실행되더라도 입력 순서대로 결과 반환

대표 시나리오:

- 전체 성공 시 `ok=True`
- 일부 optional 실패 시 `ok=False`이지만 예외 미발생
- required 실패 시 `HealthCheckError` 발생
- 예외 메시지에 password/token/secret 미노출
- `parallel=True`일 때 두 개 이상의 health check가 동시에 시작되어 전체 wall-clock 지연을 줄임

권장 테스트 파일:

- `test_docmesh_py_core/test_health.py`

### 민감정보 마스킹 / 보안

검증 대상:

- DSN/URI의 사용자명, 비밀번호, 토큰, query parameter 마스킹
- 예외 메시지 마스킹
- 로그에 access token / refresh token / client secret 미노출
- JWT raw string 미노출

대표 시나리오:

- `postgresql://user:***@host/db` → secret 미노출
- `token=abc123` 포함 문자열 → token 값 마스킹
- Keycloak/OIDC 오류 응답 원문에 secret/token이 포함되어도 최종 예외에는 숨김 처리

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

대표 시나리오:

- 대상 realm이 없으면 생성 계획 또는 생성 수행
- client가 있으면 필요한 속성만 update
- realm role/client role 누락분만 생성
- 선언에서 빠진 리소스는 삭제하지 않음
- dry-run 결과가 create/update/no-change로 분류됨

권장 테스트 파일:

- `test_docmesh_py_core/test_keycloak_provisioning.py`

### Keycloak 토큰 획득

검증 대상:

- client credentials grant
- password grant
- optional scope 전달
- 정상 응답 매핑
- 인증 실패 / 설정 오류 / 일시적 HTTP 오류 분류
- 민감정보 비노출

대표 시나리오:

- token endpoint에 올바른 form body 전달
- `access_token`, `token_type`, `expires_in` 파싱
- refresh token 존재 시 포함
- 401 → 인증 오류
- timeout / 5xx → 일시적 오류
- 잘못된 grant input → 설정 오류

권장 테스트 파일:

- `test_docmesh_py_core/test_keycloak.py`

### JWT 검증 / 사용자 정보 추출

검증 대상:

- JWKS 기반 서명 검증
- issuer 검증
- audience 선택 검증
- expiry 검증
- realm/client roles 분리 추출
- 표준 사용자 필드 매핑
- unsupported algorithm / missing claim 처리

대표 시나리오:

- 정상 JWT에서 `sub`, `preferred_username`, `email`, `realm_roles`, `client_roles` 추출
- 만료 토큰 거부
- 잘못된 `kid` 또는 서명 거부
- audience mismatch 거부
- 최소 식별 필드만 있는 토큰에서 부분 결과 허용 여부 검증

권장 테스트 파일:

- `test_docmesh_py_core/test_keycloak.py`

---

## 통합 테스트 범위

다음 항목은 단위 테스트와 분리해 운영한다.

- Keycloak 테스트 컨테이너에 대한 provisioning smoke test
- PostgreSQL `SELECT 1` 실제 수행
- MinIO bucket check 실제 수행
- Milvus 연결 및 collection 조회
- Ollama health call 실제 수행
- Langfuse 인증 check 실제 수행
- NATS connect + ping/flush 실제 수행

### 서비스별 권장 시나리오

- **Keycloak**
  - OIDC discovery 조회 성공
  - token endpoint 실제 호출 성공
  - provisioning dry-run / apply / idempotency 검증
  - 잘못된 admin credential 사용 시 인증 오류 분류 확인
- **PostgreSQL**
  - `SELECT 1` 성공
  - 잘못된 host 또는 credential로 연결 실패 분류 확인
  - pool 생성 후 close/dispose 수행 확인
- **MinIO**
  - `list_buckets()` 또는 지정 bucket 존재 확인
  - 잘못된 access/secret key로 인증 실패 확인
- **Milvus**
  - server 연결 및 collection/list 조회 성공
  - 잘못된 token 또는 uri로 실패 분류 확인
- **Ollama**
  - health endpoint 또는 `ps/list` 성공
  - host 미도달 시 timeout/connection error 확인
- **Langfuse**
  - `auth_check()` 또는 동등한 인증 검증 성공
  - 비활성화 설정 시 integration 대상에서 제외 가능함을 확인
- **NATS**
  - connect 후 flush/ping 성공
  - 재연결 옵션이 적용된 상태에서 초기 연결 실패 메시지 확인

### 실행 환경 구성

- 로컬 실행은 docker compose 또는 testcontainers 중 하나를 표준으로 정한다.
- 서비스별 readiness 조건이 충족된 뒤 테스트를 시작한다.
- integration 전용 env 파일 또는 CI secret을 사용하고, `.env.example`의 placeholder 값을 그대로 사용하지 않는다.
- 테스트 데이터는 운영 계정이 아닌 전용 테스트 realm, bucket, database, client, token으로 분리한다.
- 가능하면 테스트 종료 후 생성 리소스를 정리하되, Keycloak provisioning의 멱등성 확인에 필요한 최소 상태는 유지할 수 있다.

권장 방식:

- docker compose 또는 testcontainers 사용
- CI에서는 `integration` marker로 분리
- 로컬에서는 필요한 서비스만 선택 실행

예시:

```bash
uv run pytest -q -m "not integration"
DOCMESH_ENV=integration uv run pytest -q -m integration
DOCMESH_ENV=integration uv run pytest -q test_docmesh_py_core/test_integration_services.py
```

---

## 권장 pytest 마커

```python
pytestmark = [
    pytest.mark.unit,
]
```

추가 마커 예시:

- `@pytest.mark.unit`
- `@pytest.mark.integration`
- `@pytest.mark.security`
- `@pytest.mark.keycloak`
- `@pytest.mark.health`

이 마커들은 `pyproject.toml`의 `[tool.pytest.ini_options.markers]`에 등록해
PytestUnknownMarkWarning 없이 슬라이스 실행이 가능해야 한다.

---

## 완료 기준 매핑

| 완료 기준 | 테스트 유형 | 비고 |
| --- | --- | --- |
| 7개 외부 서비스 설정/클라이언트 제공 | 단위 테스트 | config + factory |
| 필수 env 누락/타입 오류 검증 | 단위 테스트 | config |
| 정상 연결/대표 실패 | 통합 테스트 | service별 smoke |
| 민감정보 비노출 | 단위 + 보안 테스트 | security/keycloak/health |
| 연결 확인/종료 기능 제공 | 단위 테스트 | factory/health |
| env example 문서화 | 문서 검증 테스트 | `.env.example` |
| CI 정적검사/단위테스트/민감정보 검사 | CI 파이프라인 | 별도 워크플로우 |
| Keycloak 최초 생성 | 통합 테스트 | provisioning |
| Keycloak 멱등성 | 통합 테스트 | provisioning repeat |
| Dry-run/갱신/부분실패/마스킹 | 단위 + 통합 | provisioning |
| 토큰 획득 성공/실패/비노출 | 단위 테스트 | keycloak token |
| JWT 사용자 정보/역할 추출 | 단위 테스트 | jwks fixture |
| 만료/서명 오류/audience 불일치 | 단위 테스트 | jwt negative cases |

---

## 최소 체크리스트

릴리스 전 최소한 아래 테스트는 모두 녹색이어야 한다.

- [ ] 모든 설정 모델 기본값 테스트
- [ ] 모든 필수 env 누락 테스트
- [ ] 모든 조건부 필수값 조합 테스트
- [ ] 모든 서비스 builder 인자 매핑 테스트
- [ ] 모든 서비스 `ping/check` wrapper 테스트
- [ ] health 집계 성공/실패 테스트
- [ ] 민감정보 마스킹 테스트
- [ ] Keycloak token grant 테스트
- [ ] JWT 검증 성공/실패 테스트
- [ ] `.env.example`와 설정 모델 동기화 테스트

---

## 예시 테스트 구조

```text
test_docmesh_py_core/
├── test_config.py
├── test_env_example.py
├── test_factories.py
├── test_health.py
├── test_keycloak.py
├── test_keycloak_provisioning.py
└── test_security.py
```

---

## 구현 시 주의사항

- 단위 테스트는 외부 SDK가 실제 네트워크에 접근하지 않도록 해야 한다.
- mock은 "호출 계약 검증"에만 사용하고, 설정 검증/데이터 변환은 실제 코드 경로를 사용한다.
- 시간 측정 테스트는 고정 timer 주입으로 flaky 현상을 방지한다.
- JWT 테스트는 로컬 키쌍과 JWKS fixture를 사용한다.
- 예외 메시지 검증 시 원문 전체 일치보다 "민감정보가 없다"는 성질 검증을 우선한다.

---

## 권장 실행 명령

```bash
uv run pytest -q test_docmesh_py_core
uv run pytest -q test_docmesh_py_core/test_factories.py
uv run pytest -q test_docmesh_py_core/test_keycloak.py
uv run pytest -q -m "not integration"
```

---

## 문서 유지 원칙

다음 변경 시 이 문서를 함께 갱신한다.

- 신규 외부 서비스 추가
- 환경변수 스키마 변경
- health check 방식 변경
- Keycloak provisioning/token/JWT 계약 변경
- CI 테스트 전략 변경
