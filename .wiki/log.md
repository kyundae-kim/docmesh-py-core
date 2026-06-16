# Wiki Log

> `docmesh-py-core` SDK 위키의 모든 작업을 시간순으로 기록. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`
> Actions: ingest, update, query, lint, create, archive, delete
> 500개 항목 초과 시 `log-YYYY.md`로 회전 후 새로 시작.

## [2026-06-16] query | 다음 개발 우선순위 재평가

- 질의: "다음 개발 할 것은?"
- 근거 확인:
  - `uv run pytest -q` → 46 passed, 10 warnings
  - `pytest -q` → 가상환경 밖 의존성 부재로 collection 실패
  - `test_integration_services.py` 의 `pytest.mark.keycloak`, `pytest.mark.health` 미등록 경고 확인
- 업데이트 파일:
  - `queries/future-development-roadmap.md` — 테스트 실행 계약, 마커 등록, 문서-구현 drift 기준으로 우선순위 재검증

## [2026-06-16] update | 테스트 실행 계약 정리

- 사용자 지시: 기존 로드맵의 1번(P0 테스트 체계 안정화) 진행
- 변경 사항:
  - `pyproject.toml` — `unit`, `integration`, `security`, `keycloak`, `health` pytest 마커 등록
  - `docs/test.md` — 표준 실행 명령을 `uv run pytest` 기준으로 갱신
  - `test_docmesh_py_core/test_project_contract.py` — 마커 등록/문서 실행 계약 회귀 테스트 추가
- 검증:
  - `uv run pytest -q test_docmesh_py_core/test_project_contract.py` → green
  - `uv run pytest -q` → 48 passed, 1 warning

## [2026-06-16] update | Keycloak 테스트 파일 분리

- 사용자 지시: 기존 로드맵의 2번 진행
- 변경 사항:
  - `test_docmesh_py_core/test_security.py` 신규 추가 — 인증 실패 메시지 마스킹 회귀 테스트 분리
  - `test_docmesh_py_core/test_keycloak_provisioning.py` 신규 추가 — dry-run/created/updated/failed provisioning 테스트 분리
  - `test_docmesh_py_core/test_keycloak.py` — 토큰 획득/JWT 검증 중심으로 정리, provisioning/security 테스트 제거
  - `test_docmesh_py_core/test_project_contract.py` — 문서가 기대하는 테스트 파일 구조 회귀 테스트 추가
- 검증:
  - `uv run pytest -q test_docmesh_py_core/test_project_contract.py test_docmesh_py_core/test_security.py test_docmesh_py_core/test_keycloak_provisioning.py test_docmesh_py_core/test_keycloak.py` → 12 passed
  - `uv run pytest -q` → 50 passed, 1 warning

## [2026-06-11] query | 향후 개발 로드맵 제안

- 질의: "향후 개발할 내용은? 개선할 점이나 신규 기능 등"
- 생성 파일:
  - `queries/future-development-roadmap.md` — 테스트 안정화, 관측성, 인증/저장소 고도화, 공통 유틸리티 확장 우선순위 정리
- 업데이트 파일:
  - `index.md` — Queries 섹션 등록, Total pages=16

## [2026-06-11] update | SDK 소비자 문서 구조 반영

- `docs/sdk.md` 추가 반영: `raw/project-docs/sdk.md` 심볼릭 링크 생성
- `docs/api.md` 수정 반영: `raw/project-docs/api.md` 최신 상태 참조 유지
- `raw/project-docs/config.md`, `raw/project-docs/test.md` 링크도 함께 정비
- 업데이트 파일:
  - `concepts/docmesh-sdk-overview.md` — 소비 프로젝트용 문서 구조(`sdk.md`/`api.md` 역할 분리) 추가, top-level import와 지원 서비스 최신화
  - `concepts/settings-system.md` — SQLite optional settings와 `SQLITE_*` 규칙 반영
  - `concepts/service-factory-registry.md` — `create_client(...)` 기준으로 예제 수정, SQLite 서비스 추가
  - `entities/sqlite.md` — SQLite 엔티티 페이지 신규 생성
  - `index.md` — SQLite 엔티티 등록, Total pages=15, Raw sources=5

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
