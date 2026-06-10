---
title: 민감 정보 마스킹
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [sdk-design, error-handling, logging, python]
sources: []
confidence: high
---

# 민감 정보 마스킹

`security.py`의 `mask_sensitive_value`는 로그, 에러 메시지, 헬스체크 결과에서
민감 정보가 노출되지 않도록 보호한다.

## 마스킹 대상 키워드

```python
SENSITIVE_KEYWORDS = (
    "password", "passwd", "secret", "token",
    "apikey", "api_key", "access_key", "client_secret",
)
```

이 키워드를 포함하는 문자열 패턴을 자동 감지해 값을 `***`로 교체한다.

## 처리 전략 (우선순위 순)

### 1. URL 감지

문자열이 파싱 가능한 URL이면:
- `username:password@host` 형식에서 password → `***`
- 쿼리 파라미터 중 민감 키 → `***`
- 예: `postgres://user:secret@host:5432/db` → `postgres://user:***@host:5432/db`

### 2. 키=값 패턴 감지

`password=abc123`, `token: xyz`, `secret abc` 등의 패턴에서 값 부분 → `***`
구분자: `=`, `:`, ` `
종료 조건: ` `, `&`, `,`, `;`

### 3. 키워드만 포함 (값 특정 불가)

민감 키워드가 포함되어 있지만 위 패턴이 없으면 전체를 `***`로 교체.

### 4. 민감 키워드 없음

원문 반환 (에러 메시지 보존).

## 사용 위치

- `health.py`: `ServiceHealthStatus.error`
- `keycloak.py`: 토큰 요청 에러, 네트워크 에러, 프로비저닝 실패 메시지

## 공개 API

```python
from docmesh_py_core import mask_sensitive_value

masked = mask_sensitive_value("connect to postgres://admin:p@ssw0rd@db:5432/mydb failed")
# → "connect to postgres://admin:***@db:5432/mydb failed"

masked = mask_sensitive_value(None)
# → None
```

## 한계 및 주의사항

- URL이 아닌 자유형식 에러 메시지에서 민감 값이 키워드 없이 등장하면 감지 불가.
  예: `authentication failed: abc123` — 여기서 `abc123`은 마스킹되지 않음.
- 마스킹은 best-effort. 중요한 비밀은 환경 변수로만 관리하고 문자열에 직접 포함하지 말 것.

## 관련 개념

- [[health-check-pattern]] — 에러 메시지를 마스킹해 저장
- [[keycloak-auth-flow]] — 토큰/네트워크 에러 마스킹
- [[settings-system]] — 설정 유효성 검사 에러 메시지 보안
