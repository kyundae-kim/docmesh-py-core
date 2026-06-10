# Wiki Index

> `docmesh-py-core` SDK 지식베이스 콘텐츠 카탈로그.
> 새 세션 시작 시 이 파일을 먼저 읽어 기존 페이지를 파악할 것.
> Last updated: 2026-06-10 | Total pages: 13

---

## Entities
<!-- 알파벳순 — 서비스, 라이브러리, 외부 시스템 등 구체적 존재 -->

- [[keycloak]] — IAM 서버. 토큰 발급·JWT 검증·사용자 정보·프로비저닝
- [[langfuse]] — LLM 관찰성 플랫폼. 비활성화 가능, flush() close 패턴
- [[milvus]] — 벡터 DB. `list_collections()` 헬스체크
- [[minio]] — S3 호환 오브젝트 스토리지. `list_buckets()` 헬스체크
- [[nats]] — 메시지 브로커. 비동기 연결 빌더 패턴
- [[ollama]] — 로컬 LLM 추론 서버. `ps()` 헬스체크
- [[postgres]] — 관계형 DB. SQLAlchemy Engine, `SELECT 1` 헬스체크

---

## Concepts
<!-- 알파벳순 — 설계 원칙, 패턴, 기술 개념 -->

- [[docmesh-sdk-overview]] — SDK 전체 구조, 공개 API, 모듈 역할 요약
- [[health-check-pattern]] — 다중 서비스 헬스체크 집계, required_services, 타이머 주입
- [[keycloak-auth-flow]] — 토큰 발급(grant type별), JWT 검증(HS256/RS256), 사용자 정보 추출
- [[sensitive-value-masking]] — 로그/에러 내 password·token·secret 자동 마스킹
- [[service-factory-registry]] — ServiceClientWrapper, NatsConnectionBuilder, 서비스 추가 패턴
- [[settings-system]] — pydantic-settings 계층, 환경 변수 목록, 교차 검증 규칙
- [[test-strategy]] — 유닛(mock 주입) vs 인테그레이션(DOCMESH_ENV=integration) 테스트

---

## Comparisons
<!-- 두 접근법의 비교 분석 -->

_(아직 없음)_

---

## Decisions (ADR)
<!-- 명시적 설계 결정 기록 -->

_(아직 없음)_

---

## Queries
<!-- 비자명한 질문에 대한 종합 답변 (재도출 비용이 높은 것만) -->

_(아직 없음)_
