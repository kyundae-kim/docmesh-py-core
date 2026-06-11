---
title: 헬스체크 패턴
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [service-connection, sdk-design, error-handling]
sources: []
confidence: high
---

# 헬스체크 패턴

`health.py`의 `check_all_services`는 여러 서비스의 연결 상태를
한 번에 확인하고 결과를 집계한다.

## API

```python
from docmesh_py_core import check_all_services, HealthCheckError

result = check_all_services(
    service_checks={
        "minio": minio_wrapper.ping,
        "milvus": milvus_wrapper.ping,
        "postgres": postgres_wrapper.ping,
    },
    required_services={"minio", "postgres"},  # 선택적 — 실패 시 예외 발생
)
```

## 반환 타입

```python
@dataclass(frozen=True)
class HealthCheckResult:
    ok: bool                         # 모든 서비스가 ok인지
    services: list[ServiceHealthStatus]

@dataclass(frozen=True)
class ServiceHealthStatus:
    service: str
    ok: bool
    latency_ms: int
    error: str | None                # 실패 시 마스킹된 에러 메시지
```

## required_services 동작

`required_services`에 포함된 서비스가 실패하면 즉시 `HealthCheckError`를 발생시킨다.
이후 서비스 체크는 실행되지 않는다.

```python
class HealthCheckError(RuntimeError):
    service: str   # 실패한 서비스명
    error: str     # 마스킹된 에러 설명
```

선택적 서비스(목록에 없음)가 실패해도 `result.ok=False`가 되지만 예외는 발생하지 않는다.

## 레이턴시 측정

`time.perf_counter` (기본)로 ms 단위 측정.
`timer` 파라미터로 교체 가능 → 테스트에서 결정론적 시간 주입:

```python
fake_time = iter([0.0, 0.05])  # 50ms 레이턴시 시뮬레이션
result = check_all_services(checks, timer=lambda: next(fake_time))
```

## ServiceFactoryRegistry와의 연동

```python
registry = ServiceFactoryRegistry(settings)
checks = registry.health_checks()        # Mapping[str, CheckFn]
result = check_all_services(checks, required_services={"postgres"})
```

`registry.health_checks()`는 `None` 클라이언트(비활성 서비스)를 자동 제외한다.

## 에러 메시지 보안

모든 에러 문자열은 `mask_sensitive_value`를 거쳐 저장된다.
URL의 비밀번호, 토큰, API 키가 로그/응답에 노출되지 않는다.

## 관련 개념

- [[service-factory-registry]] — `health_checks()` 제공
- [[sensitive-value-masking]] — 에러 마스킹
- [[docmesh-sdk-overview]] — 전체 SDK 구조
- [[test-strategy]] — 헬스체크 유닛 테스트 패턴
