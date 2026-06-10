---
title: NATS
created: 2026-06-10
updated: 2026-06-10
type: entity
tags: [service-connection, async]
sources: []
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

## 관련 개념

- [[service-factory-registry]] — `NatsConnectionBuilder` 반환
- [[settings-system]] — `NatsConfig`
