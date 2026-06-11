# Wiki Log

> `docmesh-py-core` SDK 위키의 모든 작업을 시간순으로 기록. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> 500개 항목 초과 시 `log-YYYY.md`로 회전 후 새로 시작.

## [2026-06-11] update | SQLite 적용 설계안 수정

- 사용자 피드백 반영: backend 선택 스위치(`DOCMESH_DB_BACKEND`) 제안 제거
- 업데이트 파일:
  - `queries/sqlite-adoption-plan.md` — switch 없는 SQLite 적용 방향으로 수정

## [2026-06-11] query | SQLite 적용 설계안

- 질의: "wiki를 참고하여 sqlite를 적용하면 어떻게 만들거야?"
- 생성 파일:
  - `queries/sqlite-adoption-plan.md` — SQLite 설정, 팩토리, 헬스체크, 테스트 설계안
- 업데이트 파일:
  - `index.md` — Queries 섹션 등록, Total pages=14

## [2026-06-10] ingest | docs/ 프로젝트 문서 4종 흡수

- `docs/prd.md` → `raw/articles/prd.md` (sha256 프론트매터 포함, 불변 원본)
- `docs/api.md` → `raw/project-docs/api.md` (심볼릭 링크, 코드와 함께 변함)
- `docs/config.md` → `raw/project-docs/config.md` (심볼릭 링크)
- `docs/test.md` → `raw/project-docs/test.md` (심볼릭 링크)
- 보강된 페이지 (concepts/):
  - `settings-system.md` — MAX_RETRIES·REQUEST_TIMEOUT 변수 전체 추가, 교차 검증 규칙·체크리스트 보강
  - `test-strategy.md` — 전체 테스트 파일 구조, pytest 마커, 릴리스 체크리스트 추가
- 보강된 페이지 (entities/):
  - `minio.md` — REQUEST_TIMEOUT_SECONDS, MAX_RETRIES 추가
  - `milvus.md` — CONNECT_TIMEOUT, REQUEST_TIMEOUT, MAX_RETRIES 추가
  - `ollama.md` — MAX_RETRIES 추가
  - `langfuse.md` — REQUEST_TIMEOUT, MAX_RETRIES 추가
  - 6개 엔티티 전체: sources frontmatter 업데이트
- `index.md`: Raw sources 카운트(4) 추가



- 소스 스캔: `docmesh_py_core/` 전체 5개 모듈 + 테스트 6개 파일
- 생성 페이지 (concepts/):
  - `docmesh-sdk-overview.md` — SDK 전체 구조
  - `settings-system.md` — pydantic-settings 계층 및 환경 변수 목록
  - `service-factory-registry.md` — ServiceClientWrapper, NatsConnectionBuilder
  - `keycloak-auth-flow.md` — 토큰 발급, JWT 검증, 사용자 정보 추출
  - `health-check-pattern.md` — 다중 서비스 헬스체크
  - `sensitive-value-masking.md` — 민감 정보 자동 마스킹
  - `test-strategy.md` — mock 레벨 + DOCMESH_ENV=integration 패턴
- 생성 페이지 (entities/):
  - `keycloak.md`, `nats.md`, `postgres.md`, `minio.md`,
  - `milvus.md`, `ollama.md`, `langfuse.md`
- `index.md` 업데이트: 13개 페이지 등록

## [2026-06-10] create | Wiki initialized

- Domain: Python 기반 범용 SDK (`docmesh-py-core`) 설계 및 개발 지식베이스
- 다루는 영역: 서비스 연결 관리, 인증 & 사용자, 공통 유틸리티, 테스트 전략
- 생성 파일:
  - `SCHEMA.md` — 도메인 정의, 컨벤션, 태그 taxonomy, 페이지 임계값
  - `index.md` — 섹션별 콘텐츠 카탈로그
  - `log.md` — 이 파일
  - `raw/articles/`, `raw/papers/`, `raw/transcripts/`, `raw/assets/`
  - `entities/`, `concepts/`, `comparisons/`, `queries/`
