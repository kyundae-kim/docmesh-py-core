---
title: 페이지네이션과 재시도 유틸리티
created: 2026-06-19
updated: 2026-06-19
type: concept
tags: [python, error-handling, sdk-design]
sources: [raw/project-docs/api.md]
confidence: high
---

# 페이지네이션과 재시도 유틸리티

`docmesh-py-core`는 서비스 연결 자체 외에도, 소비 애플리케이션이 자주 재사용하는 두 가지 범용 유틸리티를 공개한다.
하나는 `Page[T]` 페이지네이션 모델이고, 다른 하나는 `retry_call(...)` 재시도 헬퍼다.

## `Page[T]`

`Page`는 리스트 응답의 메타데이터를 함께 전달하는 dataclass다.

주요 필드:

- `items`
- `total`
- `page`
- `page_size`
- `total_pages`
- `has_next`
- `has_previous`

생성은 `Page.from_items(...)`를 사용하며, 다음 규칙을 강제한다.

- `page >= 1`
- `page_size >= 1`
- `total >= 0`
- `page`는 `total_pages`를 초과할 수 없음

즉, 소비자가 임의 dict를 직접 조립하지 않고, 일관된 페이지 메타데이터를 만들도록 돕는다.

## `retry_call(...)`

`retry_call`은 동기 함수를 대상으로 지수 백오프 재시도를 제공한다.

```python
from docmesh_py_core import retry_call

result = retry_call(
    flaky_operation,
    retry_on=(TemporaryError,),
    max_attempts=3,
)
```

핵심 규칙:

- `max_attempts < 1`이면 `ValueError`
- `retry_on`에 포함된 예외만 재시도
- 대기 시간은 `base_delay_seconds * 2**(attempt-1)` 패턴
- 최대 횟수 도달 시 마지막 예외를 그대로 다시 발생

이 유틸리티는 [[keycloak-auth-flow]] 같은 HTTP 기반 통신이나, 기타 일시적 오류가 있는 SDK 호출을 감쌀 때 유용하다.

## 설계적 의미

`Page`와 `retry_call`은 특정 서비스 전용 API가 아니라, SDK가 외부 애플리케이션에 제공하는 **작은 공통 building block**에 가깝다.
따라서 [[docmesh-sdk-overview]]의 “범용 SDK” 성격을 강화하며, 테스트에서도 독립적으로 검증하기 좋다.

## 관련 개념

- [[keycloak-auth-flow]] — 일시적 HTTP 오류 재시도 후보 영역
- [[service-factory-registry]] — 서비스 래퍼 위에서 사용할 수 있는 범용 보조 도구
- [[test-strategy]] — 입력 검증/경계 조건 회귀 테스트 대상
- [[docmesh-sdk-overview]] — SDK가 노출하는 공통 유틸리티 맥락
