# docmesh-py-core 외부 서비스 연결 SRS

## 1. 목적

이 문서는 현재 구현(v0.1.3)을 기준으로 `docmesh-py-core`의 소프트웨어 요구사항과 실제 동작 계약을 요약한다.

## 2. 시스템 범위

시스템은 다음 기능을 제공한다.

- 환경변수 기반 설정 로딩 및 검증
- 서비스별 클라이언트 팩토리 / builder
- 개별/집계 상태 확인
- 공통 오류 모델 및 민감정보 마스킹
- Keycloak 토큰 획득
- JWT 검증 및 사용자 정보 추출
- Keycloak Realm/Client/Role 프로비저닝
- 함수 경계 로깅, 재시도 helper, 구조화 서비스 이벤트 생성

시스템은 다음을 포함하지 않는다.

- 외부 서비스 설치/배포 자동화
- DB 마이그레이션 관리
- 업무 리소스 정책 생성
- 애플리케이션 비즈니스 로직

## 3. 지원 서비스

| 서비스 | 현재 제공 기능 |
| --- | --- |
| Keycloak | 인증, JWT 검증, 프로비저닝 |
| PostgreSQL | SQL 저장소 연결 |
| SQLite | 파일/메모리 저장소 연결 |
| MinIO | 객체 저장소 연결 |
| Milvus | 벡터 저장소 연결 |
| Ollama | 모델 서비스 연결 |
| Langfuse | 관측성 연결 |
| NATS | 비동기 메시징 연결 |

## 4. 기능 요구사항

### FR-1. 설정 로딩

1. 모든 외부 서비스 설정은 환경변수에서 읽어야 한다.
2. 시작 시점에 설정 객체를 생성하고 검증해야 한다.
3. 필수값 누락, 공백 문자열, 타입 오류, 범위 위반을 검출해야 한다.
4. direct `*Config()` 생성은 pydantic `ValidationError`를 그대로 노출한다.
5. `load_service_configs()` 경로는 검증 오류를 `ConfigError`로 래핑해야 한다.
6. 서비스 선택 인자가 없으면 지원 서비스 전체를 로딩해야 한다.
7. 서비스 선택 인자가 있으면 선택된 서비스만 로딩하고 나머지는 `None`이어야 한다.

### FR-2. 클라이언트 생성

1. Keycloak, PostgreSQL, SQLite, MinIO, Milvus, Ollama, Langfuse, NATS 클라이언트 생성을 지원해야 한다.
2. 각 서비스는 독립적으로 생성 가능해야 한다.
3. 서비스별 `create_*_client()` 함수는 서비스별 SDK 클라이언트 또는 wrapper를 생성해야 한다.
4. NATS는 `NatsConnectionBuilder`를 반환하고 실제 네트워크 연결은 `connect()`/`ping()`/`check()` 호출 시 수행해야 한다.
5. 다른 서비스는 팩토리 호출 시 클라이언트 객체를 즉시 생성할 수 있다.
6. PostgreSQL과 SQLite는 같은 진입점이 아니라 별도 factory를 사용한다.
7. 종료가 필요한 클라이언트는 명시적 종료 인터페이스를 제공해야 한다.

### FR-3. SQLite

1. SQLite는 파일 경로와 `:memory:`를 지원해야 한다.
2. 상대경로는 작업 디렉터리 기준으로 해석해야 한다.
3. 읽기 전용, WAL, Busy Timeout을 환경변수로 제어할 수 있어야 한다.
4. SQLite 상태 확인은 `SELECT 1` 기반이어야 한다.
5. 상위 디렉터리 생성은 자동 수행하지 않는다.

### FR-4. 상태 확인

1. 서비스별 상태 확인 함수를 제공해야 한다.
2. 전체 서비스 집계 상태 확인 인터페이스를 제공해야 한다.
3. 결과에는 최소한 `service`, `ok`, `latency_ms`, `error`가 포함되어야 한다.
4. 오류 원인에는 민감정보가 포함되면 안 된다.
5. required 서비스 실패 여부를 `required_services` 인자로 구분할 수 있어야 한다.
6. 병렬 실행 옵션을 지원해야 한다.
7. 병렬 실행 시 결과 순서는 입력 순서를 유지해야 한다.

### FR-5. 오류 처리 및 로깅

1. 설정 오류와 핵심 인증/토큰 오류는 구분 가능한 공개 오류로 제공해야 한다.
2. 필수 환경변수 누락 오류에는 변수명을 포함해야 한다.
3. Keycloak의 영구 인증 오류는 자동 재시도하면 안 된다.
4. Keycloak의 일시적 오류는 재시도 횟수와 지수 백오프로 처리할 수 있어야 한다.
5. 연결/토큰 시도 결과를 구조화 로그 이벤트로 기록할 수 있어야 한다.
6. 비밀번호, 토큰, Secret Key, DSN/URI 민감값은 로그와 예외에 기록하면 안 된다.

공개 오류 모델 최소 범위:

- `ConfigError`
- `ServiceClientError`, `ServiceClientWrapperError`
- `HealthCheckError`
- `KeycloakTokenConfigurationError`, `KeycloakTokenAuthenticationError`, `KeycloakTokenTemporaryError`, `KeycloakTokenError`
- `TokenValidationError`

### FR-6. Keycloak 프로비저닝

1. Admin client를 통해 Realm, Client, Realm Role, Client Role 생성/갱신 orchestration을 수행해야 한다.
2. 반복 실행 시 동일한 최종 상태를 보장해야 한다.
3. 선언에서 제거된 리소스를 자동 삭제하면 안 된다.
4. Dry-run을 제공해야 한다.
5. 결과를 `created`, `updated`, `unchanged`, `failed`, `planned`로 구분해야 한다.
6. 부분 실패 후 재실행 가능해야 한다.

### FR-7. Keycloak 토큰 획득

1. OIDC Token Endpoint로 Access Token을 획득해야 한다.
2. 기본 Grant는 `client_credentials`여야 한다.
3. 명시적 설정 시 `password` grant를 허용할 수 있어야 한다.
4. 선택적 `scope` 전달을 지원해야 한다.
5. 응답은 최소한 Access Token, Token Type, Expires In을 포함해야 한다.
6. 실패 시 설정 오류, 인증 실패, 일시적 오류를 구분해야 한다.
7. 토큰 원문과 Refresh Token은 로그/예외/이벤트에 노출되면 안 된다.
8. `password` grant의 username/password는 현재 설정 객체가 아니라 함수 인자로 받아야 한다.

### FR-8. JWT 검증 및 사용자 정보 추출

1. Bearer Token 또는 JWT 문자열 입력을 지원해야 한다.
2. 사용자 정보 추출 전 서명, 만료, Issuer, 선택적 Audience를 검증해야 한다.
3. HS256과 RS256 검증 경로를 지원해야 한다.
4. RS256은 JWKS 캐시와 refresh를 지원해야 한다.
5. 결과에는 최소한 `sub`, `preferred_username`, `email`, `given_name`, `family_name`, `name`, `realm_roles`, `client_roles`, `claims`를 포함해야 한다.
6. `sub`가 없으면 `jti`를 대체 식별자로 사용할 수 있어야 한다.
7. Realm Role과 Client Role을 분리 반환해야 한다.
8. 서명 실패, 만료, 필수 클레임 누락, 미지원 알고리즘을 구분 가능한 오류로 반환해야 한다.

## 5. 보안 요구사항

1. 민감정보는 환경변수 또는 Secret 관리 기능으로 주입해야 한다.
2. 운영 환경에서는 TLS 검증을 기본 활성화해야 한다.
3. TLS 비활성화는 개발/테스트 환경으로 제한해야 한다.
4. DSN/URI 출력 시 사용자명, 비밀번호, 토큰, 민감 Query Parameter를 마스킹해야 한다.
5. 환경변수 원문을 디버그 로그에 출력하면 안 된다.
6. Access Token, Refresh Token 원문을 로그/관측성 이벤트에 기록하면 안 된다.
7. production 계열 환경에서는 `KEYCLOAK_VERIFY_SSL=false`, `MINIO_SECURE=false`, `MILVUS_SECURE=false`를 허용하지 않아야 한다.

## 6. 비기능 요구사항

### NFR-1. 성능

- 상태 확인은 서비스별 독립 실행 가능
- 전체 상태 확인은 병렬 수행 가능해야 함
- 재시도는 지수 백오프를 사용해야 함

### NFR-2. 안정성

- 선택 서비스 장애가 다른 서비스 설정 로딩에 영향을 주지 않아야 함
- 반복 연결/종료 후 리소스 누수가 없어야 함
- PostgreSQL 연결 풀과 NATS 재연결 정책은 조정 가능해야 함

### NFR-3. 호환성

- Python 3.11 이상 지원
- 동기/비동기 라이브러리 특성에 맞는 인터페이스 제공
- 애플리케이션 이벤트 루프를 임의 생성/종료하지 않음

### NFR-4. 테스트 가능성

- 환경변수 입력을 격리한 단위 테스트 가능
- 외부 서비스 없이 설정 검증/마스킹/로깅 테스트 가능
- 실제 연동은 통합 테스트로 분리

## 7. 인수 기준

다음을 모두 통과해야 한다.

1. 8개 서비스 설정 객체 생성 테스트
2. 필수 환경변수 누락/타입 오류 테스트
3. 민감정보 마스킹 테스트
4. 상태 확인 응답 형식 테스트
5. 서비스 종료 인터페이스 테스트
6. SQLite `:memory:` / 읽기 전용 / 잘못된 경로 관련 테스트
7. Keycloak 프로비저닝 생성/멱등성/Dry-run/부분 실패 테스트
8. Keycloak 토큰 획득 성공/실패 테스트
9. JWT 사용자 정보 추출 및 오류 테스트
10. JWKS TTL/rotation 테스트
11. `configure_logging`, `retry_call`, `build_service_log_event` 테스트
12. integration 실행 게이트(`DOCMESH_ENV=integration`) 계약 테스트

## 8. 추적 요약

| PRD 주제 | SRS 대응 |
| --- | --- |
| 설정 | FR-1 |
| 클라이언트 생성 | FR-2 |
| SQLite | FR-3 |
| 상태 확인 | FR-4 |
| 오류/로깅 | FR-5 |
| 프로비저닝 | FR-6 |
| 토큰 획득 | FR-7 |
| JWT 검증/추출 | FR-8 |
| 보안 | 5 |
| 비기능 요구사항 | 6 |
| 완료 기준 | 7 |
