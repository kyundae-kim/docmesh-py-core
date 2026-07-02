# docmesh-py-core 외부 서비스 연결 PRD

## 1. 목적

`docmesh-py-core`는 DocMesh Python 애플리케이션이 외부 서비스를 **일관된 환경변수 설정 방식**, **서비스별 생성 함수**, **표준 헬스체크**, **민감정보 마스킹 정책**으로 연결하도록 돕는 공통 인프라 라이브러리다.

이 문서는 현재 구현 기준(v0.1.3)의 제품 범위와 사용 계약을 요약한다.

## 2. 해결하는 문제

- 서비스별 환경변수 로딩/검증 중복
- PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS, Keycloak 연동 방식 불일치
- 연결 실패 처리와 재시도 정책의 파편화
- 토큰, 비밀번호, DSN 같은 민감정보의 로그 노출 위험
- Keycloak 토큰 획득/JWT 검증/사용자 정보 추출 코드 중복

## 3. 현재 버전 목표

v0.1.3에서는 아래를 제공한다.

1. 환경변수 기반 설정 로딩/검증
2. 8개 외부 서비스용 설정 모델과 생성 함수 제공
3. 개별/집계 상태 확인 인터페이스 제공
4. 표준 오류 모델과 민감정보 마스킹 제공
5. Keycloak 토큰 획득 및 JWT 사용자 정보 추출 제공
6. Keycloak Realm/Client/Role 프로비저닝 orchestration 제공
7. 함수 경계 로깅, 구조화 이벤트, 재시도 helper 제공

## 4. 비목표

현재 범위에 포함하지 않는다.

- 외부 서비스 설치/배포 자동화
- DB 스키마/마이그레이션 관리
- MinIO bucket, Milvus collection, NATS stream의 업무 리소스 생성 정책
- Ollama 모델 다운로드/수명주기 관리
- Langfuse 대시보드 구성
- 애플리케이션 도메인 로직

## 5. 대상 사용자

- DocMesh Python 백엔드 개발자
- DevOps/플랫폼 엔지니어
- 운영 담당자

## 6. 지원 서비스

| 서비스 | 역할 | 현재 기본 확인 방식 |
| --- | --- | --- |
| Keycloak | 인증, JWT 검증, 프로비저닝 | access token fetch / JWKS 검증 |
| PostgreSQL | SQL 저장소 연결 | `SELECT 1` |
| SQLite | 로컬/테스트 저장소 | `SELECT 1` |
| MinIO | 객체 저장소 연결 | `list_buckets()` |
| Milvus | 벡터 저장소 연결 | `list_collections()` |
| Ollama | 모델 서비스 연결 | `ps()` |
| Langfuse | 트레이싱/관측성 연결 | `auth_check()` |
| NATS | 메시징 연결 | connect 후 `flush()` |

## 7. 핵심 요구사항

### PR-1. 설정

- 모든 연결 정보는 환경변수에서 읽는다.
- 시작 시점에 설정을 검증한다.
- 공백 문자열은 미설정으로 처리한다.
- Boolean/숫자형 값은 타입과 범위를 검증한다.
- `load_service_configs()` 경로의 검증 오류는 `ConfigError`로 노출한다.
- production 계열 환경에서는 일부 TLS/SSL 비활성화 값을 거부한다.

### PR-2. 클라이언트 생성

- 각 서비스 클라이언트는 독립적으로 생성할 수 있어야 한다.
- 필요한 서비스만 선택적으로 로딩할 수 있어야 한다.
- 종료가 필요한 클라이언트는 명시적 종료 인터페이스를 제공해야 한다.
- PostgreSQL과 SQLite는 **서로 다른 factory 함수**(`create_postgres_client`, `create_sqlite_client`)를 사용하되, 공통 wrapper 인터페이스(`check`, `close`)를 따른다.
- NATS만 builder를 반환하고 실제 네트워크 연결을 지연시킨다.
- 나머지 서비스는 factory 호출 시 underlying client를 즉시 생성할 수 있다.

### PR-3. SQLite 지원

- 파일 경로와 `:memory:`를 지원해야 한다.
- 상대경로는 작업 디렉터리 기준으로 해석한다.
- 읽기 전용, WAL, Busy Timeout을 환경변수로 제어할 수 있어야 한다.
- 상태 확인은 `SELECT 1` 기반이어야 한다.
- 상위 디렉터리 생성은 라이브러리 책임 범위에 포함하지 않는다.

### PR-4. 상태 확인

- 서비스별 상태 확인 함수를 제공해야 한다.
- 전체 서비스 집계 상태 확인을 제공해야 한다.
- 결과에는 서비스명, 성공 여부, 응답 시간, 마스킹된 오류 원인이 포함되어야 한다.
- required 서비스 실패 시 예외를 발생시키고, optional 서비스 실패는 결과 객체에 반영해야 한다.
- 병렬 실행 옵션을 지원해야 한다.

### PR-5. 오류/로깅

- 설정 오류, health wrapper 오류, Keycloak 토큰 오류, JWT 검증 오류를 구분 가능한 공개 타입으로 제공한다.
- 필수 환경변수 누락 시 변수명을 포함한 오류를 반환해야 한다.
- Keycloak의 일시적 토큰 오류는 재시도할 수 있어야 한다.
- 구조화 로그 이벤트를 만들 수 있어야 한다.
- 비밀번호, 토큰, Secret Key, DSN/URI 민감값은 로그/예외에서 마스킹해야 한다.

### PR-6. Keycloak 프로비저닝

- Realm, Client, Realm Role, Client Role 생성/갱신 orchestration을 지원해야 한다.
- 반복 실행 시 멱등성을 보장해야 한다.
- 선언에서 제거된 리소스를 자동 삭제하지 않아야 한다.
- Dry-run을 제공해야 한다.
- 결과를 생성/갱신/변경 없음/실패/계획으로 구분해야 한다.

### PR-7. Keycloak 인증

- OIDC Token Endpoint 기반 Access Token 획득 인터페이스를 제공해야 한다.
- 기본 grant는 client credentials여야 한다.
- 명시적 설정 시 password grant를 허용할 수 있어야 한다.
- JWT 검증 후 `sub`, `preferred_username`, `email`, `given_name`, `family_name`, `name`, `realm_roles`, `client_roles`, `claims`를 표준 필드로 반환해야 한다.
- 토큰 원문은 로그/예외에 노출되면 안 된다.

## 8. 보안 원칙

- 민감정보는 환경변수 또는 Secret 관리 기능으로 주입한다.
- 운영 환경에서는 TLS 검증을 기본 활성화한다.
- TLS 비활성화는 개발/테스트에 제한한다.
- DSN/URI 출력 시 사용자정보와 민감 Query Parameter를 마스킹한다.
- Keycloak 프로비저닝은 최소 권한 자격증명 사용을 권장한다.

## 9. 비기능 요구사항

- Python 3.11 이상 지원
- 상태 확인은 순차/병렬 실행 모두 지원
- NATS 비동기 특성에 맞는 인터페이스 제공
- 반복 연결/종료 시 리소스 누수가 없어야 함
- 실제 연동 테스트는 통합 테스트로 분리해야 함

## 10. 완료 기준

아래를 모두 만족하면 현재 계약을 충족한 것으로 본다.

1. 8개 서비스 설정 객체와 생성 인터페이스 제공
2. 필수 환경변수 누락/타입 오류 테스트 통과
3. 민감정보 비노출 테스트 통과
4. 상태 확인 및 종료 인터페이스 테스트 통과
5. SQLite `:memory:` / 파일 경로 / 읽기 전용 관련 테스트 통과
6. Keycloak 프로비저닝 생성/멱등성/Dry-run/부분 실패 테스트 통과
7. Keycloak 토큰 획득 및 JWT 검증/추출 테스트 통과
8. 로깅/재시도/구조화 이벤트 테스트 통과
9. 통합 테스트 문서와 실행 게이트(`DOCMESH_ENV=integration`) 유지

## 11. 주요 위험

| 위험 | 대응 |
| --- | --- |
| SDK별 동기/비동기 차이 | 공통 wrapper + NATS builder 분리 |
| 민감정보 로그 노출 | 중앙 마스킹 함수 및 구조화 이벤트 사용 |
| 시작 시 전체 서비스 검사로 기동 지연 | 필요한 서비스만 선택 로딩, 병렬 확인 옵션 |
| SQLite/PostgreSQL 차이 | 별도 factory + 유사 wrapper 인터페이스 |
| 과도한 Keycloak 권한 | 최소 권한 자격증명 사용 |
| 토큰 클레임 해석 불일치 | 표준 사용자 정보 스키마와 회귀 테스트 유지 |
