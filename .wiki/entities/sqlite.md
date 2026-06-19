---
title: SQLite
created: 2026-06-11
updated: 2026-06-19
type: entity
tags: [service-connection, configuration, library]
sources: [raw/articles/prd.md, raw/project-docs/config.md, raw/project-docs/api.md, raw/project-docs/sdk.md]
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

## PRD가 요구하는 동작

- `SQLITE_PATH`는 파일 경로 또는 `:memory:`를 지원해야 한다.
- 상대 경로는 애플리케이션 작업 디렉터리를 기준으로 해석한다.
- 파일이 없으면 생성 가능해야 하며, 상위 디렉터리가 없으면 명확한 오류를 반환해야 한다.
- 읽기 전용 모드, WAL, busy timeout 같은 SQLite 특화 옵션을 환경변수로 제어해야 한다.
- 로그와 오류에서 경로를 그대로 노출하기보다 필요한 경우 마스킹/축약을 고려해야 한다.

## 연결 및 헬스체크

- SQLAlchemy `Engine` 기반으로 생성된다.
- 기본 health check는 `SELECT 1`이다.
- `SQLITE_PATH=:memory:`를 사용하면 프로세스 내 메모리 DB를 만들 수 있다.
- `SQLITE_ENABLE_WAL=true`면 WAL 모드를 활성화할 수 있다.
- 네트워크 기반 ping 대신 파일 접근 가능 여부와 단순 질의 성공 여부가 핵심 신호다.

## 테스트 관점

SQLite는 운영 PostgreSQL을 완전히 대체하려는 목적보다, 개발/테스트/경량 실행 경로에서
저비용 저장소를 제공하는 역할이 크다. 따라서 [[test-strategy]]에서는 `:memory:`,
파일 생성, read-only, 잘못된 경로, PostgreSQL 선택 흐름과의 공존을 특히 검증해야 한다.

## 관련 개념

- [[settings-system]] — SQLite 환경변수와 optional settings 구조
- [[service-factory-registry]] — `create_client("sqlite")`와 wrapper 패턴
- [[docmesh-sdk-overview]] — SDK 소비자용 문서 구조와 표준 사용 흐름
- [[test-strategy]] — SQLite 관련 회귀 테스트 범위
