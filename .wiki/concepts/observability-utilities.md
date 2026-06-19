---
title: 관측성 유틸리티
created: 2026-06-19
updated: 2026-06-19
type: concept
tags: [logging, error-handling, sdk-design, python]
sources: [raw/project-docs/api.md]
confidence: high
---

# 관측성 유틸리티

`docmesh-py-core`는 서비스 연결 과정의 로그를 구조화하기 위해 `build_service_log_event(...)`
유틸리티를 공개 API로 제공한다. 이 함수는 단순 문자열 로깅 대신, 서비스명·작업명·결과·지연시간·재시도 횟수 같은
필드를 일관된 dict 구조로 정리하는 역할을 맡는다.

## 핵심 API

```python
from docmesh_py_core import build_service_log_event

event = build_service_log_event(
    service="keycloak",
    operation="fetch_access_token",
    outcome="temporary_error",
    host="https://kc.example.com",
    retry_count=1,
    latency_ms=250,
    error="token=abc123",
)
```

반환값은 dict이며, `error`와 `extra`의 민감 필드는 자동 마스킹된다.

## 설계 포인트

- `service`, `operation`, `outcome`을 기본 축으로 삼는다.
- `host`, `latency_ms`, `retry_count`, `error`는 선택 필드다.
- `extra`에 들어가는 필드도 key 이름이 `password`, `secret`, `token`, `key` 계열이면 마스킹한다.
- 에러 문자열 자체도 [[sensitive-value-masking]] 정책을 거친다.

## 사용 위치

이 유틸리티는 서비스 연결/재시도/성공/실패 이벤트를 애플리케이션 로그로 내보낼 때 적합하다.
특히 [[service-factory-registry]] 또는 [[health-check-pattern]] 주변에서 서비스별 상태를 표준 필드로 남기고,
추후 로거/트레이서/수집기로 넘기기 좋은 형태를 만든다.

## 관련 개념

- [[sensitive-value-masking]] — 오류/추가 필드 마스킹 규칙
- [[service-factory-registry]] — 서비스 생성/연결 이벤트와 결합되는 위치
- [[health-check-pattern]] — 서비스별 상태/오류를 집계하는 상위 흐름
- [[docmesh-sdk-overview]] — SDK 전반의 오류·보안 공통 컴포넌트
