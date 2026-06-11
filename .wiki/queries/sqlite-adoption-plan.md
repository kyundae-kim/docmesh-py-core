---
title: SQLite 적용 설계안
created: 2026-06-11
updated: 2026-06-11
type: query
tags: [configuration, service-connection, factory-pattern, integration-test, unit-test]
sources: [raw/articles/prd.md, raw/project-docs/config.md]
confidence: high
---

# SQLite 적용 설계안

`docmesh-py-core`에 SQLite를 넣는다면, 기존 [[postgres]] 경로를 깨지 않으면서
[[settings-system]], [[service-factory-registry]], [[health-check-pattern]],
[[test-strategy]]에 자연스럽게 편입하는 방식으로 구현하는 것이 가장 안전하다.

## 목표

- 로컬 개발과 테스트에서 PostgreSQL 대체 저장소 제공
- 기존 환경변수 우선·명시적 실패·지연 연결 원칙 유지
- 헬스체크와 팩토리 인터페이스를 PostgreSQL과 최대한 동일하게 유지

## 권장 설계

### 1. PostgreSQL과 별도 설정 모델 추가

`PostgresConfig`를 억지로 확장하지 말고 `SqliteConfig`를 별도 추가한다.

권장 필드:

- `path`: 파일 경로 또는 `:memory:`
- `readonly`: 읽기 전용 여부
- `enable_wal`: WAL 활성화 여부
- `busy_timeout_ms`: 잠금 대기 시간

이렇게 하면 PostgreSQL의 네트워크형 설정과 SQLite의 파일형 설정이 섞이지 않는다.

### 2. Settings 집계 모델에 sqlite 추가

`Settings`에 `sqlite: SqliteConfig | None` 같은 선택적 슬롯을 두고,
환경변수가 없으면 비활성화 상태로 둔다.

핵심은 "모든 서비스가 항상 필수"인 현재 구조를 그대로 복제하지 말고,
SQLite는 명시적으로 켰을 때만 활성화되게 만드는 것이다.

### 3. 팩토리에는 sqlite 서비스 엔트리 추가

[[service-factory-registry]] 패턴을 그대로 따라:

- `_build_sqlite_client(config)` 추가
- `_builders` / 지원 서비스 목록에 `sqlite` 추가
- 반환 타입은 `ServiceClientWrapper`

내부 구현은 SQLAlchemy `create_engine()`를 유지하는 편이 가장 단순하다.
예: `sqlite:///:memory:` 또는 `sqlite:////abs/path/app.db`

이렇게 하면 PostgreSQL과 SQLite 모두 "SQLAlchemy Engine + SELECT 1" 패턴으로
헬스체크와 종료 인터페이스를 공유할 수 있다.

### 4. 헬스체크는 PostgreSQL과 동일 인터페이스 유지

[[health-check-pattern]] 관점에서는 SQLite를 특수취급하지 않는 편이 좋다.

- healthcheck: `SELECT 1`
- 실패 시 마스킹된 에러 문자열 반환
- required service이면 `HealthCheckError` 발생

차이는 네트워크 연결이 아니라 파일 접근 오류가 난다는 점뿐이다.
즉 `check_all_services()`는 수정 없이 재사용하는 방향이 적합하다.

## 구현 순서

1. `config.py`
   - `SqliteConfig` 추가
   - `Settings` 집계 모델에 `sqlite` 슬롯 추가
   - SQLite 환경변수가 주어졌을 때만 활성화되도록 조건부 로드 추가

2. `factories.py`
   - `sqlite_builder` 필드 추가
   - `_build_sqlite_client()` 추가
   - `_wrap_client()`에 `sqlite` 분기 추가

3. `__init__.py`
   - `SqliteConfig` export

4. health / docs
   - 지원 서비스 목록에 sqlite 추가
   - 예시 `.env.example`와 문서 동기화

5. 테스트
   - config/factory/health/integration 테스트 추가

## 테스트 전략

[[test-strategy]]에 맞춰 두 층으로 간다.

### 유닛 테스트

- `SQLITE_PATH=:memory:` 파싱
- 상대경로/절대경로 처리
- `readonly`, `enable_wal` boolean 파싱
- `busy_timeout_ms` 범위 검증
- SQLite 환경변수가 있을 때만 sqlite 설정이 활성화되는지 확인
- SQLite를 쓰지 않는 경우 기존 postgres 경로가 그대로 동작하는지 확인
- `create_engine` 호출 인자 검증
- sqlite wrapper의 `ping()`가 `SELECT 1` 호출하는지 검증

### 통합 테스트

- `DOCMESH_ENV=integration`
- 임시 디렉터리에 sqlite 파일 생성
- registry → sqlite client 생성 → `check()` 성공
- readonly DB에 쓰기 시도 실패 시 기대 오류 확인
- 잘못된 경로/없는 상위 디렉터리에서 명확한 설정 또는 연결 오류 확인

## 내가 실제로 만들 방식

실제로는 **"새 sqlite 서비스 추가"보다 "DB 백엔드 추상화의 첫 단계"**로 구현한다.
즉:

- 외부 노출은 `postgres`와 `sqlite`를 둘 다 지원
- 내부적으로는 "관계형 저장소 엔진" 계층을 의식해 설계
- 하지만 공개 API는 현재 레지스트리 스타일을 유지

이 방식이 기존 사용자 호환성을 지키면서도,
나중에 MySQL 같은 다른 SQL 백엔드를 넣을 때 재작업을 줄인다.

## 피할 것

- `PostgresConfig`에 SQLite 필드를 억지로 섞기
- SQLite를 위해 별도 backend 선택 스위치를 도입하기
- SQLite만 별도 헬스체크 구조로 분기해서 인터페이스 깨기
- 테스트 없이 문서만 추가하고 끝내기

## 관련 페이지

- [[postgres]]
- [[settings-system]]
- [[service-factory-registry]]
- [[health-check-pattern]]
- [[test-strategy]]
- [[docmesh-sdk-overview]]
