---
title: 테스트 전략
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [test-strategy, unit-test, integration-test, python]
sources: []
confidence: high
---

# 테스트 전략

`docmesh-py-core`는 두 레벨의 테스트를 운영한다.

## 디렉토리 구조

```
test_docmesh_py_core/
├── conftest.py                  픽스처 공유
├── test_config.py               Settings 유효성 검사 유닛 테스트
├── test_env_example.py          .env.example 환경 변수 커버리지
├── test_factories.py            ServiceFactoryRegistry 유닛 테스트
├── test_health.py               check_all_services 유닛 테스트
├── test_keycloak.py             KeycloakAuthService 유닛 테스트
└── test_integration_services.py 인테그레이션 테스트 (실제 서비스 연결)
```

## 유닛 테스트 (mock 레벨)

### 특징
- 외부 서비스 불필요
- `pytest` 단독 실행으로 항상 통과해야 함
- 의존성 주입을 활용해 HTTP 클라이언트, 검증키 등을 mock으로 교체

### 핵심 패턴

**설정 주입**: `load_settings(env_dict)` 에 딕셔너리 전달
```python
settings = load_settings({
    "KEYCLOAK_URL": "https://kc.example.com",
    "KEYCLOAK_REALM": "test",
    "KEYCLOAK_CLIENT_ID": "my-app",
    "KEYCLOAK_CLIENT_SECRET": "secret",
})
```

**mock HTTP 클라이언트** (`keycloak.py` 테스트):
```python
class MockHttpClient:
    def post(self, url, *, data, headers, timeout, verify_ssl):
        return {"status_code": 200, "json": {"access_token": "tok", "token_type": "Bearer", "expires_in": 300}}

service = KeycloakAuthService(settings, http_client=MockHttpClient())
result = service.fetch_access_token()
assert result.access_token == "tok"
```

**타이머 주입** (`health.py` 테스트):
```python
times = iter([0.0, 0.1])
result = check_all_services(checks, timer=lambda: next(times))
assert result.services[0].latency_ms == 100
```

## 인테그레이션 테스트

### 활성화 방법

```bash
DOCMESH_ENV=integration pytest test_docmesh_py_core/test_integration_services.py
```

`DOCMESH_ENV=integration` 환경 변수가 없으면 `pytest.skip`으로 자동 건너뜀.
일반 `pytest` 실행은 항상 mock 레벨만 실행되어 CI에서 안전하다.

### 필요 조건
- 실제 서비스들이 기동 중이어야 함 (Docker Compose 등)
- 해당 서비스의 환경 변수가 설정되어 있어야 함

### 커버 범위
- `ServiceFactoryRegistry.get(service)` → 실제 클라이언트 생성 확인
- `ServiceClientWrapper.ping()` → 실제 서비스 응답 확인
- `KeycloakAuthService.fetch_access_token()` → 실제 토큰 발급

## conftest.py 역할

- `settings` 픽스처: 테스트용 최소 환경 변수로 `Settings` 객체 제공
- 인테그레이션 마커 감지: `DOCMESH_ENV` 체크 후 skip 처리

## Pitfalls

- `load_settings`는 `Mapping[str, str]`을 받으므로 `os.environ` 또는 딕셔너리 모두 가능
- 유닛 테스트에서 실제 환경 변수가 설정된 경우 테스트가 오염될 수 있음 →
  테스트 딕셔너리에 명시적으로 필요한 변수만 전달하고 `monkeypatch`로 환경 격리
- `ConfigError` 메시지는 `KEYCLOAK_URL` 처럼 env key 형식 → 테스트에서 이 형식으로 assert

## 관련 개념

- [[docmesh-sdk-overview]] — SDK 전체 구조
- [[settings-system]] — `load_settings` 사용법
- [[keycloak-auth-flow]] — mock HTTP 클라이언트 패턴
- [[health-check-pattern]] — 타이머 주입 패턴
