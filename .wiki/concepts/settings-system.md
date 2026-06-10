---
title: 설정 시스템 (pydantic-settings)
created: 2026-06-10
updated: 2026-06-10
type: concept
tags: [configuration, sdk-design, python]
sources: []
confidence: high
---

# 설정 시스템 (pydantic-settings)

`config.py`는 SDK의 모든 환경 변수 기반 설정을 관리한다.
pydantic-settings `BaseSettings`를 확장한 계층형 구조다.

## 계층 구조

```
DocmeshBaseSettings          ← 공통 헬퍼 (strip, bool 파싱, CSV)
  ├── CommonConfig           DOCMESH_ 접두사
  ├── KeycloakConfig         KEYCLOAK_ 접두사
  ├── PostgresConfig         POSTGRES_ 접두사
  ├── MinioConfig            MINIO_ 접두사
  ├── MilvusConfig           MILVUS_ 접두사
  ├── OllamaConfig           OLLAMA_ 접두사
  ├── LangfuseConfig         LANGFUSE_ 접두사
  └── NatsConfig             NATS_ 접두사
          ↑
       Settings (집계 모델 — 모든 서브 설정 포함)
```

## 진입점

```python
import os
from docmesh_py_core import load_settings

settings = load_settings(os.environ)
```

`load_settings(env: Mapping[str, str]) → Settings`
- 각 서브 설정을 독립적으로 빌드
- 유효성 검사 실패 시 사람 읽기 좋은 `ConfigError` 메시지 반환
- `LANGFUSE_ENVIRONMENT` 기본값을 `DOCMESH_ENV` 값으로 자동 설정

## 공통 기능 (DocmeshBaseSettings)

| 기능 | 설명 |
|------|------|
| `strip_strings` validator | 공백 제거; 빈 문자열 → `None` 변환 |
| `_parse_bool` | `"true"/"false"` 문자열 → `bool` (대소문자 무관) |
| `_parse_csv` | `"a,b,c"` 문자열 → `["a","b","c"]` |
| `env_key(field)` | 접두사 포함 환경 변수명 생성 (에러 메시지용) |

## 유효성 검사 패턴

pydantic의 `model_validator(mode="after")`를 사용해 다중 필드 간 규칙을 검증한다.

주요 교차 검증 예시:
- `KeycloakConfig`: public 클라이언트가 아니면 `client_secret` 필수
- `KeycloakConfig`: `provisioning_enabled` 시 admin 인증 모드 단일화 강제
- `NatsConfig`: `user/password`, `token`, `creds_file` 중 하나만 허용
- `Settings.apply_cross_service_defaults`: production에서 SSL 비활성화 금지

## 환경 변수 목록

### DOCMESH_*
| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DOCMESH_ENV` | `development` | 환경 식별자 |
| `DOCMESH_HEALTHCHECK_ENABLED` | `true` | 헬스체크 활성화 |

### KEYCLOAK_*
| 변수 | 필수 | 설명 |
|------|------|------|
| `KEYCLOAK_URL` | ✅ | Keycloak 서버 URL |
| `KEYCLOAK_REALM` | ✅ | 렐름명 |
| `KEYCLOAK_CLIENT_ID` | ✅ | 클라이언트 ID |
| `KEYCLOAK_CLIENT_SECRET` | 비공개 클라이언트 필수 | 클라이언트 시크릿 |
| `KEYCLOAK_VERIFY_SSL` | `true` | SSL 검증 여부 |
| `KEYCLOAK_AUDIENCE` | - | 토큰 audience 검증용 |
| `KEYCLOAK_TOKEN_GRANT_TYPE` | `client_credentials` | `client_credentials` 또는 `password` |
| `KEYCLOAK_TOKEN_USERNAME/PASSWORD` | password grant 필수 | 사용자 자격증명 |
| `KEYCLOAK_PROVISIONING_ENABLED` | `false` | 프로비저닝 활성화 |
| `KEYCLOAK_PROVISIONING_DRY_RUN` | `false` | 드라이런 모드 |

### POSTGRES_*
| 변수 | 필수 | 설명 |
|------|------|------|
| `POSTGRES_DSN` | DSN 또는 개별 변수 | 전체 DSN 문자열 |
| `POSTGRES_HOST` | DSN 없을 때 필수 | 호스트 |
| `POSTGRES_DB` | DSN 없을 때 필수 | 데이터베이스명 |
| `POSTGRES_USER/PASSWORD` | DSN 없을 때 필수 | 자격증명 |
| `POSTGRES_PORT` | `5432` | 포트 |
| `POSTGRES_POOL_SIZE` | `5` | 커넥션 풀 크기 |

### MINIO_* / MILVUS_* / OLLAMA_* / LANGFUSE_* / NATS_*
→ 각 서비스 위키 페이지 참조.

## 보안 정책

production 환경(`DOCMESH_ENV=production` 또는 `prod`)에서:
- `KEYCLOAK_VERIFY_SSL=false` → `ConfigError`
- `MINIO_SECURE=false` → `ConfigError`
- `MILVUS_SECURE=false` → `ConfigError`

[[sensitive-value-masking]] 모듈이 에러 메시지에서 민감 정보를 자동 제거한다.

## 관련 개념

- [[docmesh-sdk-overview]] — SDK 전체 구조
- [[service-factory-registry]] — 설정을 소비해 클라이언트를 생성
- [[test-strategy]] — 테스트에서 설정 주입 패턴
