---
title: docmesh-py-core SDK 개요
created: 2026-06-10
updated: 2026-06-19
type: concept
tags: [sdk-design, configuration, service-connection, auth]
sources: [raw/articles/prd.md, raw/project-docs/sdk.md, raw/project-docs/api.md]
confidence: high
---

# docmesh-py-core SDK 개요

Python 기반 범용 SDK. 외부 프로젝트/리포지토리가 `pip install` 후 즉시 서비스에 연결하고
인증 기능을 사용할 수 있도록 설계된 공통 라이브러리다.

## 설계 원칙

- **환경 변수 우선**: 모든 연결 정보는 환경 변수로 공급. 코드에 자격증명 미기재.
- **명시적 실패**: 필수 변수 누락 시 `ConfigError`로 즉시 실패. 기본값으로 침묵하지 않음.
- **선택 서비스 격리**: 선택 서비스 장애가 다른 서비스 클라이언트 생성에 연쇄 전파되지 않게 설계.
- **의존성 주입**: HTTP 클라이언트, 검증키, admin client 등은 생성자에서 교체 가능 → 유닛 테스트 용이.
- **민감정보 비노출**: 로그·예외·헬스체크 결과에 token/password/secret/DSN 원문을 남기지 않음.

## 공개 API (top-level imports)

```python
from docmesh_py_core import (
    # 설정
    Settings, load_settings, ConfigError, SqliteConfig,

    # 서비스 팩토리
    ServiceFactoryRegistry, ServiceClientWrapper, NatsConnectionBuilder,

    # 헬스체크
    check_all_services, HealthCheckError,

    # Keycloak 인증
    KeycloakAuthService, KeycloakProvisioner,
    AccessTokenResult, AuthenticatedUser,
    KeycloakTokenError, KeycloakTokenAuthenticationError,
    KeycloakTokenConfigurationError, KeycloakTokenTemporaryError,
    TokenValidationError,

    # 보안/관측성/범용 유틸
    mask_sensitive_value, build_service_log_event,
    build_settings_snapshot, to_serializable,
    retry_call, Page,
)
```

## PRD 기준 컴포넌트 맵

| 컴포넌트 | 책임 | 현재 대표 페이지 |
|------|------|------|
| 설정 컴포넌트 | 환경변수 로드, 타입 검증, 조건부 필수 규칙 | [[settings-system]] |
| 클라이언트 팩토리 | 서비스별 생성 인터페이스, 지연 연결, 종료 처리 | [[service-factory-registry]] |
| 상태 확인 | 서비스별 ping/check와 전체 집계 | [[health-check-pattern]] |
| 인증 | Keycloak 토큰 획득, JWT 검증, 사용자 정보 추출 | [[keycloak-auth-flow]] |
| 프로비저닝 | Realm/Client/Role 선언 반영, 멱등성, Dry-run | [[keycloak-provisioning]] |
| 오류/보안 공통 | 마스킹, 오류 분류, 로그 위생 | [[sensitive-value-masking]] |

## 모듈 구조

| 모듈 | 역할 |
|------|------|
| `config.py` | pydantic-settings 기반 설정 모델 (서비스별 분리) |
| `factories.py` | [[service-factory-registry]] — 서비스 클라이언트 생성·관리 |
| `health.py` | [[health-check-pattern]] — 다중 서비스 헬스체크 |
| `keycloak.py` | [[keycloak-auth-flow]], [[keycloak-provisioning]] — 토큰 발급·검증·사용자 정보·프로비저닝 |
| `security.py` | [[sensitive-value-masking]] — 로그/에러 메시지 내 민감 정보 마스킹 |
| `observability.py` | [[observability-utilities]] — 구조화 서비스 로그 이벤트 생성 |
| `snapshot.py`, `serialization.py` | [[serialization-and-snapshots]] — 안전한 설정 스냅샷과 JSON-friendly 정규화 |
| `pagination.py`, `retry.py` | [[pagination-and-retry]] — 범용 페이지 메타데이터와 지수 백오프 재시도 |

## 지원 서비스

[[keycloak]], [[postgres]], [[sqlite]], [[minio]], [[milvus]], [[ollama]], [[langfuse]], [[nats]]

SQLite는 PRD상 로컬 개발·단위 테스트·경량 통합 테스트에서 PostgreSQL 대체 저장소로
취급되며, 명시적 backend selector 대신 `settings.sqlite is not None` 여부로 선택한다.

## 표준 사용 흐름

`docs/sdk.md`는 소비 프로젝트가 아래 순서를 기본 진입 패턴으로 따르길 권장한다.^[raw/project-docs/sdk.md]

1. 환경변수 준비
2. `load_settings()` 호출
3. `ServiceFactoryRegistry(settings)` 생성
4. 필요한 서비스만 `create_client()`로 생성
5. 시작 시 `check()` 또는 `check_all_services()`로 연결 검증
6. 종료 시 `registry.close_all()` 호출

이 흐름은 [[settings-system]], [[service-factory-registry]], [[health-check-pattern]]을 하나의 앱 수명주기로 묶어 주는 상위 사용 패턴이다.

## 빠른 시작의 전제

`load_settings()`는 특정 저장소 설정만 부분적으로 읽는 얇은 헬퍼가 아니다. 현재 구현은
Keycloak, MinIO, Milvus, Ollama, NATS, Langfuse, 그리고 선택적 PostgreSQL/SQLite 설정까지 함께 검증한다.^[raw/project-docs/sdk.md]

따라서 소비 프로젝트의 "가장 작은 성공 예제"라도 실제 실행을 위해서는 DB 외의 필수 서비스 환경변수까지 준비해야 한다.
이 점은 [[settings-system]]과 `docs/config.md`를 함께 보지 않으면 놓치기 쉬운 SDK 사용상 함정이다.

## 소비 프로젝트용 문서 구조

현재 SDK 소비자는 아래 문서 순서로 진입하는 것이 가장 효율적이다.^[raw/project-docs/sdk.md]

- `docs/sdk.md` — 메인 사용자 가이드. 빠른 시작, 표준 사용 흐름, 서비스 통합 패턴, FastAPI/CLI 예제 제공
- `docs/config.md` — 환경변수와 조건부 필수 규칙의 source of truth
- `docs/api.md` — 공개 API 레퍼런스. 함수/클래스 역할, 반환값, 예외, 범용 유틸리티 계약 중심
- `docs/test.md` — SDK 자체 및 소비 프로젝트의 검증 전략
- `docs/prd.md` — 왜 이런 구조와 완료 기준을 요구하는지 설명하는 요구사항 문서

## 테스트 전략

- 유닛 테스트: `./test_docmesh_py_core/` — mock 레벨
- 인테그레이션 테스트: `DOCMESH_ENV=integration` 환경 변수로 활성화
- 상세: [[test-strategy]]

## 범용 유틸리티 묶음

- [[observability-utilities]] — 구조화 로그 이벤트
- [[serialization-and-snapshots]] — 안전한 스냅샷/직렬화
- [[pagination-and-retry]] — 페이지네이션과 재시도 보조 도구
