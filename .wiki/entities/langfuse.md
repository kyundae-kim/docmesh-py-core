---
title: Langfuse
created: 2026-06-10
updated: 2026-06-10
type: entity
tags: [service-connection, logging]
sources: [raw/articles/prd.md, raw/project-docs/config.md]
confidence: high
---

# Langfuse

LLM 관찰성(Observability) 플랫폼. 프롬프트 트레이싱, 평가, 비용 추적.
헬스체크는 `auth_check()`. `close_fn`은 `flush()`(배치 전송 완료 대기).

## 특이 사항

- `LANGFUSE_ENABLED=false`로 비활성화 가능. 비활성 시 클라이언트를 아예 생성하지 않음.
- `LANGFUSE_ENVIRONMENT` 미설정 시 `DOCMESH_ENV` 값을 자동으로 사용.
- `flush()`를 close_fn으로 사용해 종료 시 미전송 이벤트를 모두 전송한다.

## 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `LANGFUSE_ENABLED` | - | `true` | 활성화 여부 |
| `LANGFUSE_HOST` | enabled일 때 필수 | - | 서버 URL |
| `LANGFUSE_PUBLIC_KEY` | enabled일 때 필수 | - | 공개 키 |
| `LANGFUSE_SECRET_KEY` | enabled일 때 필수 | - | 시크릿 키 |
| `LANGFUSE_ENVIRONMENT` | - | `DOCMESH_ENV` 값 | 환경 식별자 |
| `LANGFUSE_RELEASE` | - | - | 릴리즈 버전 태그 |
| `LANGFUSE_REQUEST_TIMEOUT_SECONDS` | - | `10` | API 요청 제한 시간 |
| `LANGFUSE_MAX_RETRIES` | - | `3` | 일시적 전송 오류 최대 재시도 횟수 |

## 관련 개념

- [[service-factory-registry]] — Langfuse 클라이언트 생성 (None 반환 조건 포함)
- [[settings-system]] — `LangfuseConfig`
