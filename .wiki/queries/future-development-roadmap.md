---
title: 향후 개발 로드맵 제안
created: 2026-06-11
updated: 2026-06-16
type: query
tags: [roadmap, sdk-design, test-strategy, service-connection, error-handling]
sources: [raw/articles/prd.md, raw/project-docs/sdk.md, raw/project-docs/api.md, raw/project-docs/test.md, raw/project-docs/config.md]
confidence: medium
---

# 향후 개발 로드맵 제안

현재 위키의 [[docmesh-sdk-overview]], [[settings-system]], [[service-factory-registry]],
[[health-check-pattern]], [[keycloak-auth-flow]], [[test-strategy]]를 기준으로 보면,
`docmesh-py-core`의 다음 단계는 **기능 추가 그 자체**보다도
**운영 안정성 / 테스트 신뢰성 / 공통 유틸리티 확장** 쪽 우선순위가 더 높다.

2026-06-16 기준으로 현재 저장소 상태를 다시 검증하면,
`uv run pytest -q` 는 46개 테스트가 모두 통과한다.
다만 일반 `pytest -q` 는 현재 셸에 의존성이 직접 설치되어 있지 않아
collection 단계에서 실패한다. 즉, 테스트 성공 계약이 사실상 "프로젝트 가상환경/uv를 통해 실행"으로 묶여 있다.

추가로 `uv run pytest -q` 결과에서 `pytest.mark.keycloak`, `pytest.mark.health` 가
등록되지 않아 PytestUnknownMarkWarning 10건이 발생했다.
또 `[[test-strategy]]` 와 `docs/test.md` 에는 `test_security.py`,
`test_keycloak_provisioning.py` 가 권장/기대 구조로 적혀 있지만,
현재 실제 테스트 파일은 `test_keycloak.py` 하나에 보안/프로비저닝 검증이 섞여 있다.

즉, "다음 기능"을 넣기 전에 테스트 실행 계약과 테스트 구조 문서-구현 정합성을 먼저 단단하게 만드는 편이 투자 대비 효과가 가장 크다.

아래는 추천 우선순위다.

## 1. P0 — 테스트 체계 안정화

가장 먼저 할 일은 테스트 계층을 문서대로 더 엄격하게 분리하는 것이다.
[[test-strategy]]는 단위 테스트와 integration 테스트를 분리하고,
`DOCMESH_ENV=integration`일 때만 실제 서비스 검증을 수행하도록 정의한다.

2026-06-16 진행 메모:

- `pyproject.toml`에 `unit`, `integration`, `security`, `keycloak`, `health` 마커 등록 완료
- `docs/test.md` 실행 예제를 `uv run pytest` 기준으로 정리 완료
- `test_project_contract.py` 추가로 테스트 실행 계약과 마커 등록 상태를 회귀 테스트로 고정
- `test_security.py`, `test_keycloak_provisioning.py` 분리 완료 — 문서가 기대하는 테스트 구조와 저장소 구조 일치

그런데 현재 실행 관점에서는 아래 리스크가 있다.

- `LANGFUSE_ENVIRONMENT` 기본값이 현재 셸의 `DOCMESH_ENV` 영향을 받기 쉬움
- integration 테스트가 환경에 따라 의도치 않게 실제 연결을 시도할 수 있음
- `pytest.mark.health`, `pytest.mark.keycloak` 같은 마커 등록이 누락되면 경고가 발생함

### 권장 작업

1. 단위 테스트에서 환경변수를 항상 명시적으로 격리
2. integration 전용 fixture / helper를 중앙화
3. `keycloak`, `health`, `unit`, `security` 등 pytest 마커를 `pyproject.toml`에 등록
4. 외부 서비스 credential/hostname 검증 실패 시 skip 메시지를 더 명확히 표준화
5. 테스트 가이드와 실제 테스트 파일 목록을 다시 맞춤

### 기대 효과

- 개발자 로컬 환경에 따라 테스트가 흔들리는 문제 감소
- CI에서 unit/integration 파이프라인 분리 용이
- [[settings-system]]의 환경변수 정책과 [[test-strategy]]의 실행 정책이 실제로 일치

## 2. P1 — 관측성/오류 처리 완성도 보강

PRD는 구조화 로그, 재시도 정책, 민감정보 비노출, 서비스별 오류 분류를 강하게 요구한다.^[raw/articles/prd.md]
현재 위키상 강점은 [[sensitive-value-masking]]과 [[health-check-pattern]]이 이미 정리되어 있다는 점이지만,
다음 보강 여지가 남아 있다.

### 권장 신규 기능

- **구조화 로깅 유틸리티**
  - service name, operation, latency, retry count, outcome를 공통 필드로 남기는 helper
- **재시도/backoff 정책 공통화**
  - 특히 Keycloak, Langfuse, HTTP 기반 서비스에 대해 일시적 오류 재시도 래퍼 제공
- **헬스체크 병렬화 옵션**
  - PRD의 "전체 확인 시 병렬 수행 권장"을 반영해 `check_all_services()` 확장 검토
- **오류 타입 표준화**
  - Postgres/SQLite/MinIO/Milvus/Ollama/NATS에서도 사용자에게 노출할 예외 메시지 형태를 더 일관화

### 왜 지금 필요한가

서비스 수가 늘수록 개별 SDK 오류 형식이 제각각이면 소비 프로젝트에서 예외 처리 분기가 늘어난다.
`docmesh-py-core`가 진짜 공통 SDK가 되려면 [[service-factory-registry]] 수준을 넘어
"운영 시 어떤 로그/에러를 받는가"까지 표준화해야 한다.

## 3. P1 — 문서와 실제 구현의 갭 제거

위키 기준으로는 [[test-strategy]]에 `test_security.py`, `test_keycloak_provisioning.py` 같은
권장 파일이 명시돼 있고, [[keycloak-auth-flow]]에도 프로비저닝 검증 중요도가 높게 적혀 있다.
이 영역은 문서상 중요도에 비해 실제 회귀 방어가 아직 약한 축으로 보인다.

### 권장 작업

- Keycloak provisioning 전용 단위 테스트 파일 분리
- 민감정보 마스킹 전용 테스트 파일 분리
- `.env.example` / docs / 실제 설정 모델 간 drift 검출 테스트 강화
- 프로비저닝 dry-run / partial failure / idempotency 시나리오 확장

### 기대 효과

- [[keycloak-auth-flow]]와 실제 품질 보증 수준의 정합성 상승
- 보안/운영 이슈를 릴리스 전에 더 일찍 차단

## 4. P2 — 저장소 계층 확장

SQLite가 들어오면서 [[sqlite]]와 [[postgres]]의 공통점이 더 많아졌다.
지금은 서비스 이름 기준 분기만으로도 충분하지만,
중기적으로는 관계형 저장소 계층을 조금 더 명시적으로 정리할 가치가 있다.

### 권장 개선점

- "관계형 DB wrapper" 개념 정리 (`Engine` 공통 계약 문서화)
- 소비 프로젝트 예제에서 `settings.sqlite` / `settings.postgres` 선택 패턴 공식화
- 트랜잭션/세션 관리 예제 추가
- SQLite WAL, readonly, `:memory:` 시나리오별 운영 가이드 보강

### 신규 기능 후보

- 마이그레이션 도구 자체를 넣는 것은 비목표지만,
  **migration-friendly connection helper** 정도는 추가 가능
- 테스트/로컬 개발용 ephemeral DB bootstrap helper

이 단계는 [[sqlite-adoption-plan]]의 후속 작업으로 보는 편이 자연스럽다.

## 5. P2 — 인증 기능의 운영형 보강

[[keycloak-auth-flow]]를 보면 이미 토큰 발급, JWT 검증, 프로비저닝 골격은 갖췄다.
다음 확장은 "기능 추가"보다 "운영형 성숙도"에 가깝다.

### 권장 신규 기능

- **JWKS 캐시 TTL / refresh 전략**
- **Key rotation 대응**
- **Audience / issuer 검증 정책의 문서-코드 일치 테스트 강화**
- **권한/클레임 매핑 helper**
  - 예: 역할/score/커스텀 클레임을 소비 프로젝트에서 더 쉽게 쓰는 보조 함수

### 이유

현재 위키에도 JWKS 캐시가 인스턴스 수명 동안 유지된다는 주석이 있다.
운영 환경에서는 키 롤오버 대응이 다음 단계 핵심 과제가 될 가능성이 높다.

## 6. P3 — SDK 공통 유틸리티 확장

SCHEMA의 도메인 설명에는 "향후 추가될 범용 기능 (로깅, 페이지네이션, 직렬화 등)"이 이미 포함돼 있다.
하지만 현재 위키와 공개 API는 아직 서비스 연결/인증 중심이다.
즉, 앞으로의 신규 기능은 아래 방향이 자연스럽다.

### 후보 기능

- **구조화 로깅 facade**
- **직렬화/역직렬화 helper**
- **페이지네이션 응답 모델**
- **공통 오류 모델 / result type**
- **서비스별 설정 스냅샷(민감정보 마스킹 버전) 출력 helper**

이 축은 `docmesh-py-core`를 "연결 SDK"에서
"DocMesh 계열 서비스의 공통 Python foundation SDK"로 키우는 방향이다.

## 추천 실행 순서

1. **테스트 체계 안정화**
2. **마커 등록 + integration gating 개선**
3. **Keycloak provisioning / security 테스트 보강**
4. **구조화 로깅 + 재시도/backoff 유틸리티**
5. **헬스체크 병렬화 및 오류 타입 표준화**
6. **저장소/인증 운영형 기능 고도화**
7. **직렬화·페이지네이션 등 범용 유틸리티 확장**

## 지금 바로 backlog로 옮기기 좋은 항목

- `pytest` 마커 등록 및 테스트 환경 격리 정비
- `test_security.py` 추가
- `test_keycloak_provisioning.py` 추가
- `check_all_services()` 병렬 실행 옵션 설계
- 공통 retry/backoff helper 설계
- JWKS 캐시 TTL 전략 설계
- 구조화 로깅 API 초안 작성

## 관련 페이지

- [[docmesh-sdk-overview]]
- [[settings-system]]
- [[service-factory-registry]]
- [[health-check-pattern]]
- [[keycloak-auth-flow]]
- [[test-strategy]]
- [[sqlite-adoption-plan]]
