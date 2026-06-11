# Wiki Schema

## Domain

Python 기반 범용 SDK (`docmesh-py-core`) 설계 및 개발 지식베이스.

외부 프로젝트/리포지토리에서 공통 기능을 재사용할 수 있도록 제공하는 SDK로,
다음 영역을 포함한다:

- **서비스 연결 관리** — 여러 외부 서비스 연결·헬스체크·환경 변수 기반 설정
- **인증 & 사용자** — 인증(auth), 사용자 정보 획득, score 확인 등 auth 관련 기능
- **공통 유틸리티** — 향후 추가될 범용 기능 (로깅, 페이지네이션, 직렬화 등)
- **테스트 전략** — 유닛 테스트(mock), 인테그레이션 테스트(DOCMESH_ENV=integration)

이 위키는 설계 결정, 패턴, 외부 참고 자료, 구현 노하우를 축적한다.

---

## Conventions

- 파일명: lowercase, 하이픈, 공백 없음 (e.g., `service-factory.md`)
- 모든 위키 페이지는 YAML frontmatter로 시작
- `[[wikilinks]]`로 페이지 간 링크 (페이지당 최소 2개 outbound)
- 페이지 수정 시 `updated` 날짜 업데이트
- 새 페이지는 `index.md` 의 해당 섹션에 추가 (알파벳순)
- 모든 작업은 `log.md`에 append
- 3개 이상의 소스를 종합하는 페이지에는 단락 끝에 `^[raw/articles/source.md]` provenance 마커 추가

---

## Frontmatter

```yaml
---
title: 페이지 제목
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/source-name.md]
confidence: high | medium | low
contested: true          # 선택적 — 미결 모순이 있을 때
contradictions: [other-page-slug]
---
```

---

## Tag Taxonomy

### 아키텍처 / 설계
- `sdk-design` — SDK 전반 구조, 레이어, 설계 원칙
- `service-connection` — 외부 서비스 연결, 헬스체크, 팩토리
- `configuration` — 환경 변수, pydantic-settings, .env 관리
- `factory-pattern` — 서비스/클라이언트 팩토리 레지스트리

### 인증 & 사용자
- `auth` — 인증 흐름, 토큰, 세션
- `user-info` — 사용자 프로필 획득, 정규화
- `score` — 점수/등급 조회 기능

### 구현
- `python` — Python 언어 특화 구현 사항
- `async` — 비동기(asyncio) 패턴
- `error-handling` — 예외 계층, retry, fallback
- `serialization` — 직렬화/역직렬화, 스키마
- `logging` — 구조화 로깅, tracing

### 테스트
- `unit-test` — 유닛 테스트, mock 전략
- `integration-test` — 인테그레이션 테스트 (`DOCMESH_ENV=integration`)
- `test-strategy` — 테스트 설계 원칙, fixture

### 외부 참조
- `pattern` — 업계 검증된 패턴 (12-factor, hexagonal 등)
- `library` — 외부 라이브러리/패키지 평가
- `benchmark` — 성능 측정 결과

### 메타
- `comparison` — 두 접근법의 비교 분석
- `decision` — 명시적 설계 결정(ADR)
- `roadmap` — 향후 계획, 기능 아이디어
- `pitfall` — 알려진 함정, 주의 사항

> **규칙:** 위 taxonomy에 없는 태그는 먼저 여기에 추가한 뒤 사용한다.

---

## Page Thresholds

| 상황 | 행동 |
|------|------|
| 엔티티/개념이 2개 이상 소스에서 언급됨 | 새 페이지 생성 |
| 하나의 소스에서 핵심적으로 다룸 | 새 페이지 생성 |
| 지나가는 언급, 주변 세부사항 | 페이지 생성 안 함 |
| 페이지가 200줄 초과 | 서브토픽으로 분리 + 교차 링크 |
| 내용이 완전히 대체됨 | `_archive/`로 이동 |

---

## Entity Pages

한 엔티티(서비스, 라이브러리, 개념)당 하나의 페이지. 포함 내용:
- 개요 / 무엇인지
- 핵심 사실과 날짜
- 다른 엔티티와의 관계 (`[[wikilinks]]`)
- 소스 참조

## Concept Pages

하나의 개념/주제당 하나의 페이지. 포함 내용:
- 정의 / 설명
- 현재 지식 상태
- 미결 질문 또는 논쟁
- 관련 개념 (`[[wikilinks]]`)

## Comparison Pages

두 접근법의 나란한 분석. 포함 내용:
- 무엇을 비교하고 왜
- 비교 차원 (표 형식 선호)
- 결론 또는 종합
- 소스

## Decision Pages (ADR)

명시적 설계 결정. 포함 내용:
- 컨텍스트 (왜 결정이 필요했는가)
- 검토한 대안들
- 결정 및 근거
- 결과 / 트레이드오프

---

## Update Policy

새 정보가 기존 내용과 충돌할 때:
1. 날짜 확인 — 최신 소스가 일반적으로 우선
2. 진짜 모순이면 날짜+소스 포함해 두 입장을 모두 기록
3. frontmatter에 `contradictions: [page-name]` 표시
4. lint 보고서에서 사용자 검토 요청
