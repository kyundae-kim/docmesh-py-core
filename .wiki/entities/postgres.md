---
title: PostgreSQL
created: 2026-06-10
updated: 2026-06-10
type: entity
tags: [service-connection]
sources: [raw/articles/prd.md, raw/project-docs/config.md]
confidence: high
---

# PostgreSQL

관계형 데이터베이스. SQLAlchemy Engine으로 연결 관리.
`ServiceClientWrapper`로 감싸 `ping()`이 `SELECT 1`을 실행한다.

## 연결 방식 (둘 중 하나)

| 방식 | 환경 변수 |
|------|-----------|
| DSN 문자열 | `POSTGRES_DSN` |
| 개별 변수 | `POSTGRES_HOST` + `POSTGRES_DB` + `POSTGRES_USER` + `POSTGRES_PASSWORD` |

## 주요 설정

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `POSTGRES_PORT` | `5432` | 포트 |
| `POSTGRES_SSLMODE` | `prefer` | SSL 모드 |
| `POSTGRES_POOL_SIZE` | `5` | 커넥션 풀 크기 |
| `POSTGRES_MAX_OVERFLOW` | `10` | 최대 초과 연결 수 |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | `10` | 연결 타임아웃 |

## 관련 개념

- [[service-factory-registry]] — SQLAlchemy Engine 생성
- [[settings-system]] — `PostgresConfig`
