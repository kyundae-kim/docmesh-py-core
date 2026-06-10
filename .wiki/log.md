# Wiki Log

> `docmesh-py-core` SDK 위키의 모든 작업을 시간순으로 기록. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> 500개 항목 초과 시 `log-YYYY.md`로 회전 후 새로 시작.

## [2026-06-10] ingest | docmesh-py-core 코드베이스 초기 분석

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
