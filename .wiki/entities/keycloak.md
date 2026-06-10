---
title: Keycloak
created: 2026-06-10
updated: 2026-06-10
type: entity
tags: [auth, user-info, service-connection]
sources: []
confidence: high
---

# Keycloak

오픈소스 IAM(Identity and Access Management) 솔루션.
`docmesh-py-core`에서 인증 및 사용자 정보 획득의 핵심 서비스.

## 역할
- 액세스 토큰 발급 (OAuth2 / OpenID Connect)
- JWT 검증 및 사용자 정보 파싱
- 렐름/클라이언트/역할 프로비저닝

## 환경 변수 접두사: `KEYCLOAK_`

필수: `KEYCLOAK_URL`, `KEYCLOAK_REALM`, `KEYCLOAK_CLIENT_ID`
상세: [[settings-system]], [[keycloak-auth-flow]]

## 구현 클래스
- `KeycloakAuthService` — 토큰 발급, JWT 검증, 사용자 정보 추출
- `KeycloakProvisioner` — 렐름/클라이언트/역할 자동 생성

## 관련 개념
- [[keycloak-auth-flow]] — 상세 인증 흐름
- [[service-factory-registry]] — `registry.get("keycloak")` 반환값
