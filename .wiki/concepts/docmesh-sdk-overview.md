---
title: docmesh-py-core SDK 개요
created: 2026-06-10
updated: 2026-06-11
type: concept
tags: [sdk-design, configuration, service-connection, auth]
sources: [raw/project-docs/sdk.md, raw/project-docs/api.md]
confidence: high
---

# docmesh-py-core SDK 개요

Python 기반 범용 SDK. 외부 프로젝트/리포지토리가 `pip install` 후 즉시 서비스에 연결하고
인증 기능을 사용할 수 있도록 설계된 공통 라이브러리다.

## 설계 원칙

- **환경 변수 우선**: 모든 연결 정보는 환경 변수로 공급. 코드에 자격증명 미기재.
- **명시적 실패**: 필수 변수 누락 시 `ConfigError`로 즉시 실패. 기본값으로 침묵하지 않음.
- **zero-extra-deps 원칙**: 외부 프로젝트는 필요한 서비스 드라이버만 설치.
- **의존성 주입**: HTTP 클라이언트, 검증키 등은 생성자에서 교체 가능 → 유닛 테스트 용이.

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

    # 보안 유틸
    mask_sensitive_value,
)
```

## 모듈 구조

| 모듈 | 역할 |
|------|------|
| `config.py` | pydantic-settings 기반 설정 모델 (서비스별 분리) |
| `factories.py` | [[service-factory-registry]] — 서비스 클라이언트 생성·관리 |
| `health.py` | [[health-check-pattern]] — 다중 서비스 헬스체크 |
| `keycloak.py` | [[keycloak-auth-flow]] — 토큰 발급·검증·사용자 정보·프로비저닝 |
| `security.py` | [[sensitive-value-masking]] — 로그/에러 메시지 내 민감 정보 마스킹 |

## 지원 서비스

[[keycloak]], [[postgres]], [[minio]], [[milvus]], [[ollama]], [[langfuse]], [[nats]], [[sqlite]]

## 소비 프로젝트용 문서 구조

현재 SDK 소비자는 아래 문서 순서로 진입하는 것이 가장 효율적이다.^[raw/project-docs/sdk.md]

- `docs/sdk.md` — 메인 사용자 가이드. 빠른 시작, 표준 사용 흐름, 서비스 통합 패턴, FastAPI/CLI 예제 제공
- `docs/config.md` — 환경변수와 조건부 필수 규칙의 source of truth
- `docs/api.md` — 공개 API 레퍼런스. 함수/클래스 역할, 반환값, 예외 중심
- `docs/test.md` — SDK 자체 및 소비 프로젝트의 검증 전략

핵심 분리 원칙:

- `sdk.md`는 **어떻게 붙여서 개발하는가**를 설명한다.
- `api.md`는 **어떤 공개 API가 있고 무엇을 반환하는가**를 설명한다.
- 사용 흐름 예제는 `sdk.md`에 두고, 시그니처/반환값/예외는 `api.md`에 유지한다.

## 테스트 전략

- 유닛 테스트: `./test_docmesh_py_core/` — mock 레벨
- 인테그레이션 테스트: `DOCMESH_ENV=integration` 환경 변수로 활성화
- 상세: [[test-strategy]]
