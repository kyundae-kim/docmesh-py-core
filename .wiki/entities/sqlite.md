---
title: SQLite
created: 2026-06-11
updated: 2026-06-11
type: entity
tags: [service-connection, configuration, library]
sources: [raw/project-docs/config.md, raw/project-docs/api.md, raw/project-docs/sdk.md]
confidence: high
---

# SQLite

SQLite는 `docmesh-py-core`에서 PostgreSQL과 별도 설정 집합으로 다루는 경량 관계형 저장소다.
주로 로컬 개발, 단위 테스트, 경량 통합 테스트, 단일 파일 기반 애플리케이션 시나리오에 적합하다.

## 설정 키

- `SQLITE_PATH`
- `SQLITE_READONLY`
- `SQLITE_ENABLE_WAL`
- `SQLITE_BUSY_TIMEOUT_MS`

## 사용 패턴

소비 프로젝트는 명시적 backend selector 대신 아래처럼 `settings.sqlite` 존재 여부로 분기한다.

```python
if settings.sqlite is not None:
    db = registry.create_client("sqlite")
elif settings.postgres is not None:
    db = registry.create_client("postgres")
else:
    raise RuntimeError("No database is configured")
```

## 연결 및 헬스체크

- SQLAlchemy `Engine` 기반으로 생성된다.
- 기본 health check는 `SELECT 1`이다.
- `SQLITE_PATH=:memory:`를 사용하면 프로세스 내 메모리 DB를 만들 수 있다.
- `SQLITE_ENABLE_WAL=true`면 WAL 모드를 활성화할 수 있다.

## 관련 개념

- [[settings-system]] — SQLite 환경변수와 optional settings 구조
- [[service-factory-registry]] — `create_client("sqlite")`와 wrapper 패턴
- [[docmesh-sdk-overview]] — SDK 소비자용 문서 구조와 표준 사용 흐름
