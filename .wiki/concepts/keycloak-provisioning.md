---
title: Keycloak 프로비저닝
created: 2026-06-19
updated: 2026-06-19
type: concept
tags: [auth, configuration, error-handling, decision]
sources: [raw/articles/prd.md]
confidence: medium
---

# Keycloak 프로비저닝

`docmesh-py-core`의 Keycloak 프로비저닝은 Realm, Client, Realm Role, Client Role을
선언형 설정에서 읽어 생성·갱신하는 운영용 컴포넌트다.^[raw/articles/prd.md]
PRD 기준 핵심 목표는 **반복 실행해도 같은 최종 상태를 유지하는 멱등성**과,
**Dry-run/부분 실패 식별을 통한 안전한 변경**이다.^[raw/articles/prd.md]

## 책임 범위

- Keycloak Admin API를 사용해 관리 대상 리소스를 조회한다.
- 선언에 없지만 기존에 존재하는 리소스를 자동 삭제하지 않는다.
- 누락된 리소스는 생성하고, 관리 대상 속성 차이는 갱신한다.
- 결과를 `created`, `updated`, `unchanged`, `failed`처럼 구분해 반환한다.
- Admin 자격증명과 생성된 Client Secret은 로그에 노출하지 않는다.

## 설정 전제

프로비저닝은 기본적으로 비활성화되어 있으며, 명시적으로 켰을 때만 동작해야 한다.
`KEYCLOAK_PROVISIONING_ENABLED=true`이면 Admin API 인증 정보가 필요하고,
인증 방식은 service account 또는 관리자 username/password 중 하나만 선택하는 것이
PRD와 설정 모델의 공통 계약이다. 자세한 변수 목록은 [[settings-system]]을 따른다.

## 안전장치

### Dry-run

Dry-run은 실제 변경 없이 어떤 Realm/Client/Role이 생성 또는 갱신될지만 보여준다.
운영 반영 전에 선언 상태를 검토하는 기본 절차로 취급하는 것이 안전하다.

### 자동 삭제 금지

선언에서 빠졌다는 이유만으로 Realm, Client, Role을 자동 삭제하지 않는다.
인증 시스템은 파괴적 변경의 영향이 크므로, 제거는 별도 운영 절차로 다루는 편이 낫다.

### 부분 실패 복구

한 번의 실행에서 일부 리소스만 성공할 수 있으므로 결과는 완료/실패 항목을 명확히
구분해야 하며, 동일 선언으로 재실행 가능해야 한다. 이 특성은 [[test-strategy]]의
멱등성/부분 실패 회귀 테스트로 계속 보존되어야 한다.

## 테스트 기대치

PRD의 완료 기준상 다음 검증이 필요하다.

- 최초 생성 테스트
- 동일 설정 반복 실행 시 추가 변경이 없는 멱등성 테스트
- Dry-run 테스트
- 기존 리소스 갱신 테스트
- 부분 실패 식별 테스트
- Admin 인증정보 및 Client Secret 비노출 테스트

## 관련 개념

- [[keycloak-auth-flow]] — 토큰 획득·검증과 같은 Keycloak 기능의 나머지 축
- [[settings-system]] — 프로비저닝 관련 환경변수와 조건부 필수 규칙
- [[sensitive-value-masking]] — Admin secret과 오류 메시지 마스킹
- [[test-strategy]] — provisioning mock/integration 테스트 전략
