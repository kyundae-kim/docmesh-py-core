---
title: 직렬화와 설정 스냅샷
created: 2026-06-19
updated: 2026-06-19
type: concept
tags: [serialization, configuration, logging, python]
sources: [raw/project-docs/api.md]
confidence: high
---

# 직렬화와 설정 스냅샷

`docmesh-py-core`는 설정이나 모델 객체를 안전하게 외부로 내보내기 위해
`to_serializable(...)`와 `build_settings_snapshot(...)`를 공개 API로 노출한다.
이 조합은 **복합 Python 객체를 JSON-friendly 구조로 바꾸고**, 그 뒤 **민감 정보를 제거한 설정 스냅샷**을 만드는 데 쓰인다.

## `to_serializable(value)`

이 함수는 다음 타입을 재귀적으로 정규화한다.

- dataclass
- Pydantic model
- `datetime`, `date`
- `Path`
- `Enum`
- `dict`, `list`, `tuple`, `set`

직렬화되지 않는 나머지 값은 문자열로 변환한다. 따라서 운영 로그, 디버그 덤프, API 응답용 사전 변환기로 유용하다.

## `build_settings_snapshot(settings)`

설정 객체를 스냅샷으로 남길 때는 단순 직렬화만으로 충분하지 않다.
이 함수는 먼저 `to_serializable`로 구조를 평탄화한 뒤, 필드 이름을 기준으로 민감 정보를 추가로 마스킹한다.

핵심 동작:

- `secret`, `password`, `token`, `key` 계열 필드는 `***` 처리
- `server`, `dsn`, `uri`, `url`, `host`, `endpoint` 계열은 endpoint-like 값으로 간주해 자격증명 축약
- 일반 문자열도 [[sensitive-value-masking]] 규칙을 거쳐 best-effort 마스킹

## 왜 별도 스냅샷 API가 필요한가

설정 객체는 디버깅에 매우 유용하지만, 그대로 출력하면 DSN/host/token/client secret 노출 위험이 있다.
`build_settings_snapshot`은 [[settings-system]]을 관찰 가능하게 만들면서도,
PRD가 요구하는 민감정보 비노출 원칙을 유지하는 안전장치다.

## 사용 시점

- 애플리케이션 시작 시 현재 설정 상태를 진단하고 싶을 때
- 오류 리포트에 “어떤 설정이 켜져 있었는지”를 남기고 싶을 때
- 테스트에서 설정 모델이 어떤 값으로 해석됐는지 비교할 때

## 관련 개념

- [[settings-system]] — 스냅샷 대상이 되는 설정 모델
- [[sensitive-value-masking]] — 문자열 단위 마스킹 규칙
- [[observability-utilities]] — 구조화 로그와 함께 쓰기 좋은 보조 API
- [[docmesh-sdk-overview]] — 설정/보안 공통 컴포넌트 맥락
