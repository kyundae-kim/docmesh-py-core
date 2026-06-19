---
title: NATS
created: 2026-06-10
updated: 2026-06-19
type: entity
tags: [service-connection, async]
sources: [raw/articles/prd.md, raw/project-docs/config.md, raw/project-docs/sdk.md, raw/project-docs/api.md]
confidence: high
---

# NATS

고성능 메시지 브로커. docmesh-py-core에서 비동기 메시징에 사용.
다른 서비스와 달리 `ServiceClientWrapper` 대신 `NatsConnectionBuilder`를 반환한다.

## 이유

NATS 연결(`nats.connect`)은 코루틴이므로 팩토리가 직접 연결을 생성할 수 없다.
빌더 패턴으로 연결 파라미터를 캡슐화하고, 사용자가 `await builder.connect()`로 연결한다.

## 인증 모드 (하나만 선택)

| 모드 | 환경 변수 |
|------|-----------|
| 사용자/비밀번호 | `NATS_USER` + `NATS_PASSWORD` (함께 필수) |
| 토큰 | `NATS_TOKEN` |
| 크레덴셜 파일 | `NATS_CREDS_FILE` |
| 인증 없음 | 위 변수 미설정 |

## 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `NATS_SERVERS` | ✅ | - | 콤마 구분 서버 URL 목록 |
| `NATS_NAME` | - | `docmesh-py-core` | 연결 식별자 |
| `NATS_CONNECT_TIMEOUT_SECONDS` | - | `10` | 연결 타임아웃 |
| `NATS_MAX_RECONNECT_ATTEMPTS` | - | `10` | 재연결 시도 횟수 |

## 소비 프로젝트에서의 사용법

`create_client("nats")`는 연결된 동기 클라이언트를 반환하지 않는다. 소비 프로젝트는
반환된 `NatsConnectionBuilder`를 받아 아래처럼 비동기 문맥에서 연결해야 한다.^[raw/project-docs/sdk.md]

```python
builder = registry.create_client("nats")
connection = await builder.connect()
await connection.flush()
```

연결 확인만 필요하면 `await builder.check()` 패턴을 사용할 수 있다. 이 차이를 놓치면
다른 서비스와 동일하게 `.check()`를 즉시 동기 호출하려다 통합 오류가 발생하기 쉽다.

## 관련 개념

- [[service-factory-registry]] — `NatsConnectionBuilder` 반환
- [[settings-system]] — `NatsConfig`
