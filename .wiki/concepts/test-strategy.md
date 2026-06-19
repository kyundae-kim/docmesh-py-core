---
title: 테스트 전략
created: 2026-06-10
updated: 2026-06-19
type: concept
tags: [test-strategy, unit-test, integration-test, python]
sources: [raw/articles/prd.md, raw/project-docs/test.md]
confidence: high
---

# 테스트 전략

`docmesh-py-core`는 두 레벨의 테스트를 운영한다.

## 테스트 계층

1. **단위 테스트** — mock/stub 중심, 외부 네트워크 연결 없이 수행
2. **통합 테스트** — 실제 서비스 또는 테스트 컨테이너, 별도 실행 조건
3. **보안/회귀 테스트** — 민감정보 비노출, 잘못된 토큰/서명/audience 처리

## 테스트 파일 구조

```
test_docmesh_py_core/
├── conftest.py                     공유 픽스처
├── test_config.py                  Settings 유효성 검사 유닛 테스트
├── test_env_example.py             .env.example 환경 변수 커버리지
├── test_factories.py               ServiceFactoryRegistry 유닛 테스트
├── test_health.py                  check_all_services 유닛 테스트
├── test_keycloak.py                KeycloakAuthService 유닛 테스트
├── test_keycloak_provisioning.py   KeycloakProvisioner 유닛 테스트
├── test_security.py                민감정보 마스킹 테스트
└── test_integration_services.py   통합 테스트 (DOCMESH_ENV=integration)
```

## 단위 테스트 — 핵심 패턴

### 설정 주입

```python
from docmesh_py_core import load_settings

settings = load_settings({
    "KEYCLOAK_URL": "https://kc.example.com",
    "KEYCLOAK_REALM": "test",
    "KEYCLOAK_CLIENT_ID": "my-app",
    "KEYCLOAK_CLIENT_SECRET": "secret",
    # 필요한 변수만 명시, 나머지는 기본값
})
```

### mock HTTP 클라이언트 (keycloak 테스트)

```python
class MockHttpClient:
    def post(self, url, *, data, headers, timeout, verify_ssl):
        return {
            "status_code": 200,
            "json": {"access_token": "tok", "token_type": "Bearer", "expires_in": 300}
        }

from docmesh_py_core import KeycloakAuthService
service = KeycloakAuthService(settings, http_client=MockHttpClient())
result = service.fetch_access_token()
assert result.access_token == "tok"
```

### 타이머 주입 (health 테스트)

```python
times = iter([0.0, 0.1])
result = check_all_services(checks, timer=lambda: next(times))
assert result.services[0].latency_ms == 100
```

### mock admin 클라이언트 (provisioning 테스트)

```python
class MockAdminClient:
    def get_realm(self, realm): return None
    def create_realm(self, payload): return {"id": realm}
    # ...

provisioner = KeycloakProvisioner(settings, admin_client=MockAdminClient())
result = provisioner.provision()
```

## 단위 테스트 범위

### 설정 로더

- 필수 환경변수 누락 감지
- 공백 문자열을 누락으로 처리
- bool / 정수형 파싱 및 범위 검증
- 조건부 필수값 + 상호 배타 조건 검증
- `LANGFUSE_ENABLED=false` 시 Langfuse key 미입력 허용
- `POSTGRES_DSN` 우선 적용
- SQLite `:memory:` / 상대경로 / 잘못된 상위 디렉터리 검증

### 서비스 팩토리

- 서비스별 builder가 올바른 SDK 생성자를 호출하는지
- `Langfuse enabled=false`면 `None` 반환
- NATS가 event loop를 임의 생성/종료하지 않는지
- 각 wrapper의 `check()`가 서비스별 health call을 수행하는지
- PostgreSQL/SQLite가 같은 상위 저장소 선택 흐름에서 호환되는지

### 헬스체크 집계

- 전체 성공 시 `ok=True`
- optional 실패 시 `ok=False`, 예외 미발생
- required 실패 시 `HealthCheckError` 발생
- 예외 메시지에 password/token/secret 미노출
- 병렬 모드에서도 결과 순서 유지

### 민감정보 마스킹

- DSN/URI의 비밀번호·토큰·query parameter 마스킹
- `token=abc123` 포함 문자열에서 token 값 마스킹
- Keycloak/OIDC 오류 응답 원문의 secret/token 숨김
- SQLite 파일 경로가 과도하게 노출되지 않는지 검증

### Keycloak 토큰 획득

- client_credentials / password grant 분기
- 선택적 `scope` 전달
- `access_token`, `token_type`, `expires_in`, `refresh_token` 파싱
- 401 → 인증 오류 / timeout, 5xx → 일시적 오류 / 잘못된 input → 설정 오류

### JWT 검증 / 사용자 정보 추출

- 정상 JWT에서 `sub`, `preferred_username`, `email`, `realm_roles`, `client_roles` 추출
- 만료 토큰 거부
- 잘못된 서명/kid 거부, audience mismatch 거부
- 표준 클레임 일부 누락 시 부분 결과 허용 여부 검증

### Keycloak 프로비저닝

- realm/client/role 생성·갱신 판단
- dry-run 시 실제 변경 없음
- 선언에서 빠진 리소스는 삭제하지 않음
- 부분 실패 결과 분류
- 반복 실행 시 멱등성 유지

## 통합 테스트

### 활성화 방법

```bash
DOCMESH_ENV=integration uv run pytest -q test_docmesh_py_core/test_integration_services.py
# 또는 마커 기반
DOCMESH_ENV=integration uv run pytest -q -m integration
```

`DOCMESH_ENV=integration` 없으면 `pytest.skip`으로 자동 건너뜀.

### 서비스별 검증 항목

| 서비스 | 검증 내용 |
|--------|-----------|
| Keycloak | token endpoint 실제 호출, provisioning dry-run/apply/idempotency |
| PostgreSQL | `SELECT 1` 성공, 잘못된 credential 시 실패 분류 |
| SQLite | `:memory:`/파일 경로/읽기 전용/잘못된 경로 분기 |
| MinIO | `list_buckets()` 성공, 잘못된 access/secret key 실패 |
| Milvus | 연결 + `list_collections()` 성공 |
| Ollama | `ps()` 성공, host 미도달 시 timeout |
| Langfuse | `auth_check()` 성공, 비활성화 시 대상 제외 |
| NATS | connect + flush/ping 성공 |

### 실행 환경

- 로컬: docker compose 또는 testcontainers
- CI: `unit`과 분리, 브랜치/야간/릴리스 파이프라인에서 활성화
- 테스트 데이터: 전용 realm, bucket, database, client — 운영 자원 재사용 금지

## pytest 마커

```python
# 단위 테스트 파일 상단
pytestmark = [pytest.mark.unit]

# 통합 테스트 파일 상단
pytestmark = [pytest.mark.integration]
```

마커 종류: `unit`, `integration`, `security`, `keycloak`, `health`

## 권장 실행 명령

```bash
# 단위 테스트만 (기본 CI)
uv run pytest -q test_docmesh_py_core

# 통합 테스트
DOCMESH_ENV=integration uv run pytest -q test_docmesh_py_core/test_integration_services.py

# 특정 모듈
uv run pytest -q test_docmesh_py_core/test_keycloak.py
```

## PRD 완료 기준과 직접 연결되는 체크리스트

- [ ] 8개 서비스 설정 객체/클라이언트 생성 인터페이스 검증
- [ ] 필수 env 누락/잘못된 타입 테스트
- [ ] 서비스별 정상 연결 및 대표 실패 분류 테스트
- [ ] SQLite `:memory:`/read-only/잘못된 경로 테스트
- [ ] 민감정보 비노출 테스트
- [ ] 각 클라이언트의 check/close 계약 테스트
- [ ] Keycloak provisioning 생성/갱신/멱등성/Dry-run/부분 실패 테스트
- [ ] Keycloak token 획득 성공/실패/비노출 테스트
- [ ] JWT 검증 성공/만료/서명 오류/audience 불일치 테스트
- [ ] `.env.example`와 설정 모델 동기화 테스트

## Pitfalls

- 단위 테스트에서 실제 환경변수가 설정된 경우 테스트가 오염될 수 있음 → `monkeypatch`로 환경 격리
- `ConfigError` 메시지는 `KEYCLOAK_URL` 처럼 env key 형식 → 이 형식으로 assert
- JWT 테스트는 로컬 키쌍과 JWKS fixture를 사용해 JWKS endpoint 호출 없이 수행
- 예외 메시지 검증 시 원문 전체 일치보다 "민감정보가 없다"는 성질 검증 우선

## 관련 개념

- [[docmesh-sdk-overview]] — SDK 전체 구조
- [[settings-system]] — `load_settings` 사용법
- [[keycloak-auth-flow]] — mock HTTP 클라이언트 패턴
- [[keycloak-provisioning]] — provisioning 회귀 테스트 범위
- [[health-check-pattern]] — 타이머 주입 패턴
- [[sensitive-value-masking]] — 마스킹 검증 대상
