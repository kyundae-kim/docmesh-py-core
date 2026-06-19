---
title: Keycloak 인증 흐름
created: 2026-06-10
updated: 2026-06-19
type: concept
tags: [auth, user-info, score, python, error-handling]
sources: [raw/articles/prd.md, raw/project-docs/api.md]
confidence: high
---

# Keycloak 인증 흐름

`keycloak.py`의 `KeycloakAuthService`가 담당하는 세 가지 핵심 기능:
1. **액세스 토큰 발급** (`fetch_access_token`)
2. **JWT 토큰 검증 + 사용자 정보 추출** (`extract_user_info`)
3. **JWKS 기반 RS256 서명 검증**

프로비저닝은 같은 모듈에 있지만 운영 성격이 달라 별도 페이지 [[keycloak-provisioning]]으로 분리한다.

## KeycloakAuthService 초기화

```python
service = KeycloakAuthService(
    settings,                          # Settings 객체
    http_client=None,                  # 기본: _UrllibKeycloakHttpClient (stdlib만 사용)
    verification_key="my-hs256-key",  # HS256 검증용 (선택)
    allowed_algorithms=["HS256"],      # 기본: ["HS256"]
)
```

`http_client`는 `KeycloakHttpClient` Protocol을 구현하면 교체 가능.
테스트에서 mock HTTP 클라이언트를 주입해 실제 Keycloak 없이 유닛 테스트할 수 있다.
또한 RS256 검증의 JWKS 캐시는 `KEYCLOAK_JWKS_CACHE_TTL_SECONDS`로 제어된다.

## 액세스 토큰 발급

```python
result: AccessTokenResult = service.fetch_access_token(scope="openid")
# result.access_token, .token_type, .expires_in, .refresh_token, .scope
```

### Grant Type별 동작

| `KEYCLOAK_TOKEN_GRANT_TYPE` | 필요 변수 | 설명 |
|----------------------------|-----------|------|
| `client_credentials` (기본) | `client_secret` | 서비스 계정 인증 |
| `password` | `token_username`, `token_password` | 사용자 자격증명 인증 |

PRD 기준으로 `scope`는 선택적 입력이며, 응답에는 최소 `access_token`, `token_type`,
`expires_in`이 포함되어야 한다. Refresh token이 내려오면 함께 전달할 수 있다.

### 에러 계층

```
KeycloakError (RuntimeError)
└── KeycloakTokenError
    ├── KeycloakTokenConfigurationError  설정 오류 (재시도 불가)
    ├── KeycloakTokenAuthenticationError 인증 실패 400/401/403 (재시도 불가)
    └── KeycloakTokenTemporaryError      네트워크/5xx (재시도 가능)
```

호출자는 `KeycloakTokenTemporaryError`만 재시도 대상으로 처리하면 된다.

## 사용자 정보 추출 (JWT 파싱)

```python
user: AuthenticatedUser = service.extract_user_info(token)
# Bearer 접두사 자동 제거
```

### AuthenticatedUser 필드

| 필드 | JWT 클레임 | 설명 |
|------|-----------|------|
| `sub` | `sub` / `jti` | 사용자 고유 식별자 |
| `preferred_username` | `preferred_username` | 사용자명 |
| `email` | `email` | 이메일 |
| `given_name` / `family_name` / `name` | 동일 | 이름 정보 |
| `realm_roles` | `realm_access.roles` | 렐름 역할 목록 |
| `client_roles` | `resource_access.<client>.roles` | 클라이언트별 역할 맵 |
| `claims` | 전체 JWT payload | 원시 클레임 딕셔너리 |

> **score 확인**: `claims`에서 커스텀 클레임 접근 가능.  
> `user.claims.get("score")` 또는 역할 기반 권한 레벨 활용.

PRD는 표준 클레임이 일부 비어 있어도 `sub` 또는 토큰 고유 식별 정보가 있으면
부분 결과를 허용하는 방향을 제시한다.

## JWT 서명 검증

### HS256

```python
service = KeycloakAuthService(settings, verification_key="shared-secret")
```
- 대칭 키로 HMAC-SHA256 서명 검증
- `hmac.compare_digest`로 timing-safe 비교

### RS256

```python
service = KeycloakAuthService(settings, allowed_algorithms=["RS256"])
```
- JWKS endpoint에서 공개키 조회 (`/realms/{realm}/protocol/openid-connect/certs`)
- `kid` 헤더로 키 선택
- 순수 Python 구현 (cryptography 라이브러리 불필요): 모듈러 거듭제곱 + PKCS#1 v1.5 패딩 검증
- JWKS 응답은 인메모리 캐시 (`_jwks_cache`)
- TTL이 만료되면 JWKS를 다시 가져온다.
- 검증 중 key rotation 또는 `kid` 변경이 감지되면 JWKS를 1회 강제 refresh해 재검증한다.

> **주의**: JWKS 캐시는 `KEYCLOAK_JWKS_CACHE_TTL_SECONDS` 기본값(`300`)의 영향을 받는다.
> `0`이면 사실상 캐시를 무기한 재사용하므로, 키 롤오버 민감도가 높다면 TTL 정책을 명시적으로 관리해야 한다.

## 클레임 유효성 검증

`_validate_registered_claims`가 수행:
1. `iss` — `{url}/realms/{realm}` 과 일치해야 함
2. `exp` — 현재 시각보다 미래여야 함
3. `aud` — `KEYCLOAK_AUDIENCE` 설정 시 목록에 포함 여부 확인

PRD는 여기서 검증 실패를 최소한 `서명 오류 / 만료 / audience 불일치 / 필수 클레임 누락 /
지원하지 않는 알고리즘` 수준으로 구분 가능한 오류로 다루길 요구한다.

## 엔드포인트 속성

```python
service.issuer         # {url}/realms/{realm}
service.token_endpoint # {issuer}/protocol/openid-connect/token
service.jwks_endpoint  # {issuer}/protocol/openid-connect/certs
```

## 관련 개념

- [[settings-system]] — `KeycloakConfig` 환경 변수
- [[service-factory-registry]] — `registry.get("keycloak")` 반환 값
- [[keycloak-provisioning]] — 선언형 Realm/Client/Role 반영
- [[sensitive-value-masking]] — 에러 메시지 보안
- [[test-strategy]] — mock HTTP 클라이언트를 이용한 유닛 테스트 패턴
