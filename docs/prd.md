# DocMesh Python Core 외부 서비스 연결 PRD

## 1. 문서 개요

- **제품명:** docmesh-py-core
- **문서 상태:** Draft
- **대상 버전:** v0.1.0
- **작성일:** 2026-06-09

## 2. 배경

DocMesh는 인증, 데이터 저장, 객체 저장소, 벡터 검색, LLM 실행, 관측성,
메시징 기능을 여러 외부 서비스에 위임한다. 각 애플리케이션이 연결 및 설정
로직을 개별 구현하면 설정 방식과 장애 처리 정책이 달라지고, 비밀정보가
코드에 포함될 위험이 있다. 특히 인증 영역에서는 토큰 발급, JWT 검증,
사용자 정보 추출 방식이 애플리케이션마다 달라지면 보안 정책과 권한 해석이
불일치할 수 있다.

`docmesh-py-core`는 Python 기반 DocMesh 애플리케이션이 외부 서비스에
일관된 방식으로 연결할 수 있도록 공통 설정과 클라이언트 생성 기능을
제공한다.

## 3. 목적

외부 서비스 연결 정보를 환경변수에서 안전하게 읽고 검증하여, DocMesh의
Python 애플리케이션이 동일한 인터페이스와 운영 정책으로 외부 서비스를
사용할 수 있게 한다. Keycloak 기반 인증에서는 토큰 획득, 검증, 사용자
클레임 해석을 공통화하여 인증 연동 코드를 단순화한다.

## 4. 목표

1. Keycloak, PostgreSQL, MinIO, Milvus, Ollama, Langfuse, NATS 연결 설정을
   환경변수로 관리한다.
2. Keycloak Realm, Client, Role을 환경변수에 선언된 상태로 프로비저닝한다.
3. 애플리케이션 시작 시 필수 설정의 누락 및 형식 오류를 빠르게 탐지한다.
4. 서비스별 클라이언트 생성과 연결 확인 방식을 표준화한다.
5. 비밀번호, 토큰, Secret Key 등 민감정보가 로그나 예외 메시지에 노출되지
   않도록 한다.
6. 로컬, 개발, 스테이징, 운영 환경에서 코드 변경 없이 환경변수만으로
   연결 대상을 변경할 수 있게 한다.
7. 연결 실패 시 서비스명과 원인은 확인할 수 있되 민감정보는 제외된
   명확한 오류를 제공한다.
8. Keycloak 토큰 엔드포인트를 통해 Access Token을 가져오는 공통 인터페이스를
   제공한다.
9. JWT에서 사용자 식별자, 사용자명, 이메일, 역할 등 표준화된 사용자 정보를
   추출하는 공통 인터페이스를 제공한다.

## 5. 비목표

- 외부 서비스 자체의 설치, 배포 및 계정 생성
- 데이터베이스 스키마와 마이그레이션 관리
- MinIO Bucket, Milvus Collection, NATS Stream의 업무별 생성 정책
- Ollama 모델 다운로드 및 수명주기 관리
- Langfuse 대시보드와 평가 정책 구성
- 애플리케이션의 도메인 로직 구현

## 6. 대상 사용자

- DocMesh Python 백엔드 개발자
- 배포 환경을 구성하는 DevOps 및 플랫폼 엔지니어
- 외부 서비스 연결 상태를 점검하는 운영 담당자

## 7. 지원 외부 서비스

| 서비스 | 주요 용도 | 기본 연결 검증 |
| --- | --- | --- |
| Keycloak | 사용자 인증, JWT 검증 및 Realm/Client/Role 프로비저닝 | OIDC Discovery, JWKS 조회 또는 Admin API 확인 |
| PostgreSQL | 메타데이터 및 업무 데이터 저장 | `SELECT 1` 실행 |
| MinIO | 문서 및 파일 객체 저장 | Bucket 존재 여부 또는 서버 응답 확인 |
| Milvus | 임베딩 벡터 저장 및 검색 | 서버 연결 상태 확인 |
| Ollama | 임베딩 및 생성형 모델 호출 | 서버 버전 또는 모델 목록 조회 |
| Langfuse | LLM 트레이싱, 관측성 및 평가 | 인증된 API 요청 또는 클라이언트 검증 |
| NATS | 비동기 이벤트 및 메시지 전달 | 서버 연결 및 Ping/Pong 확인 |

## 8. 기능 요구사항

### FR-1. 환경변수 기반 설정

- 모든 외부 서비스 연결 정보는 환경변수에서 읽어야 한다.
- 소스 코드에 환경별 URL, 사용자명, 비밀번호, API Key를 하드코딩하지
  않아야 한다.
- 환경변수는 애플리케이션 시작 시 한 번 읽고 타입과 필수값을 검증해야
  한다.
- 공백 문자열은 필수값이 없는 것으로 처리해야 한다.
- Boolean 값은 대소문자와 관계없이 `true` 또는 `false` 형식으로
  처리해야 한다.
- 숫자형 값은 유효 범위를 검증해야 한다.

### FR-2. 서비스별 클라이언트 생성

- 각 서비스는 독립적으로 설정을 불러오고 클라이언트를 생성할 수 있어야
  한다.
- 클라이언트 생성 시 연결을 강제하지 않는 지연 연결을 우선 지원해야 한다.
- 애플리케이션은 필요한 서비스의 클라이언트만 생성할 수 있어야 한다.
- 클라이언트 종료가 필요한 경우 명시적인 종료 인터페이스를 제공해야 한다.

### FR-3. 연결 상태 확인

- 서비스별 연결 확인 함수를 제공해야 한다.
- 전체 서비스 상태를 한 번에 확인할 수 있는 집계 인터페이스를 제공해야
  한다.
- 결과에는 서비스명, 성공 여부, 응답 시간, 민감정보가 제거된 오류 원인을
  포함해야 한다.
- 선택 서비스의 장애가 전체 프로세스 시작 실패로 이어지는지는 설정으로
  구분할 수 있어야 한다.

### FR-4. 오류 처리

- 필수 환경변수가 누락되면 해당 변수명을 포함한 설정 오류를 발생시켜야
  한다.
- 인증 실패, 연결 거부, DNS 오류, 타임아웃을 구분 가능한 오류로
  전달해야 한다.
- 재시도를 지원하는 서비스는 서비스별 최대 재시도 횟수를 적용하고,
  일시적 오류에 지수 백오프를 적용할 수 있어야 한다.
- 설정 오류와 영구적인 인증 오류는 자동 재시도하지 않아야 한다.
- 연결 제한 시간, 요청 제한 시간, 최대 재시도 횟수는 공통 설정을
  사용하지 않고 서비스별 환경변수로 관리해야 한다.
- 특정 제한 시간이나 재시도 정책이 필요하지 않은 서비스에는 관련
  환경변수를 정의하지 않아야 한다.

### FR-5. 로깅 및 관측성

- 연결 시도, 성공, 실패, 재시도, 종료 이벤트를 구조화된 로그로 남길 수
  있어야 한다.
- 로그에는 서비스명과 대상 호스트를 포함할 수 있다.
- 비밀번호, 토큰, Secret Key, 전체 연결 문자열은 로그에 포함하지 않아야
  한다.
- Langfuse 자체 연결 실패가 핵심 애플리케이션 기능을 중단시키지 않도록
  선택적으로 구성할 수 있어야 한다.

### FR-6. Keycloak 프로비저닝

- Keycloak Admin API를 사용하여 Realm, Client, Realm Role 및 Client Role을
  생성하거나 선언된 설정으로 갱신할 수 있어야 한다.
- 프로비저닝은 반복 실행해도 동일한 최종 상태를 유지하는 멱등성을
  보장해야 한다.
- 기존 리소스를 조회한 뒤 누락된 리소스는 생성하고, 관리 대상 속성의
  차이는 갱신해야 한다.
- 선언에서 제거된 Realm, Client 또는 Role을 자동 삭제하지 않아야 한다.
- Dry-run 모드에서 실제 변경 없이 생성 및 갱신 예정 항목을 확인할 수
  있어야 한다.
- 프로비저닝 결과에는 생성, 갱신, 변경 없음, 실패 항목을 구분하여
  제공해야 한다.
- 부분 실패 시 이미 완료된 작업과 실패한 작업을 식별할 수 있어야 하며,
  동일 설정으로 안전하게 재실행할 수 있어야 한다.
- Admin API 인증정보와 생성된 Client Secret은 로그에 노출하지 않아야 한다.

### FR-7. Keycloak 토큰 획득

- Keycloak OIDC Token Endpoint를 호출하여 Access Token을 가져오는 인터페이스를
  제공해야 한다.
- 기본 토큰 획득 방식은 Client Credentials Grant를 사용해야 한다.
- 필요 시 명시적 설정을 통해 Password Grant를 사용할 수 있어야 한다.
- 토큰 요청 시 `scope`를 선택적으로 전달할 수 있어야 한다.
- 토큰 응답에는 최소한 Access Token, Token Type, Expires In을 포함해야 하며,
  Refresh Token이 제공되는 경우 함께 전달할 수 있어야 한다.
- 토큰 획득 실패 시 설정 오류, 인증 실패, 일시적 HTTP 오류를 구분 가능한
  오류로 전달해야 한다.
- 토큰 원문과 Refresh Token은 로그, 예외 메시지, 디버그 출력에 노출하지
  않아야 한다.

### FR-8. 토큰 검증 및 사용자 정보 추출

- Bearer Token 또는 JWT 문자열에서 사용자 정보를 추출하는 인터페이스를
  제공해야 한다.
- 사용자 정보 추출 전 서명, 만료 시각, Issuer, 선택적 Audience 검증을
  수행해야 한다.
- 추출 결과에는 최소한 `sub`, `preferred_username`, `email`,
  `given_name`, `family_name`, `name`, `realm_roles`, `client_roles`,
  원본 클레임 맵을 포함해야 한다.
- 표준 클레임이 누락된 경우에도 `sub` 또는 토큰 고유 식별 정보가 있으면
  부분 결과를 반환할 수 있어야 한다.
- Realm Role과 Client Role은 Keycloak 토큰 구조를 해석하여 각각 분리된
  컬렉션으로 제공해야 한다.
- 서명 검증 실패, 만료 토큰, 필수 클레임 누락, 지원하지 않는 알고리즘은
  구분 가능한 오류로 전달해야 한다.
- 토큰에서 추출한 사용자 정보 객체는 애플리케이션이 권한 검사와 감사 로그에
  바로 사용할 수 있는 일관된 필드명을 가져야 한다.

## 9. 환경변수 명세

### 9.1 공통

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `DOCMESH_ENV` | 아니요 | `development` | 실행 환경 식별자 |
| `DOCMESH_HEALTHCHECK_ENABLED` | 아니요 | `true` | 연결 상태 확인 활성화 여부 |

공통 연결 제한 시간, 요청 제한 시간 및 최대 재시도 횟수는 제공하지 않는다.

### 9.2 Keycloak

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `KEYCLOAK_URL` | 예 | 없음 | Keycloak 기본 URL |
| `KEYCLOAK_REALM` | 예 | 없음 | 인증 Realm |
| `KEYCLOAK_CLIENT_ID` | 예 | 없음 | OIDC Client ID |
| `KEYCLOAK_CLIENT_SECRET` | 조건부 | 없음 | Confidential Client 사용 시 Secret |
| `KEYCLOAK_VERIFY_SSL` | 아니요 | `true` | TLS 인증서 검증 여부 |
| `KEYCLOAK_AUDIENCE` | 아니요 | 없음 | JWT 검증 대상 Audience |
| `KEYCLOAK_TOKEN_GRANT_TYPE` | 아니요 | `client_credentials` | 토큰 획득에 사용할 Grant Type |
| `KEYCLOAK_TOKEN_SCOPE` | 아니요 | 없음 | 토큰 요청 시 전달할 Scope |
| `KEYCLOAK_TOKEN_USERNAME` | 조건부 | 없음 | Password Grant 사용 시 사용자명 |
| `KEYCLOAK_TOKEN_PASSWORD` | 조건부 | 없음 | Password Grant 사용 시 비밀번호 |
| `KEYCLOAK_REQUEST_TIMEOUT_SECONDS` | 아니요 | `10` | OIDC 및 JWKS 요청 제한 시간 |
| `KEYCLOAK_MAX_RETRIES` | 아니요 | `3` | 일시적 HTTP 오류 최대 재시도 횟수 |
| `KEYCLOAK_PROVISIONING_ENABLED` | 아니요 | `false` | 프로비저닝 활성화 여부 |
| `KEYCLOAK_PROVISIONING_DRY_RUN` | 아니요 | `false` | 변경 없이 실행 계획만 확인할지 여부 |
| `KEYCLOAK_ADMIN_REALM` | 조건부 | `master` | Admin API 인증 Realm |
| `KEYCLOAK_ADMIN_CLIENT_ID` | 조건부 | `admin-cli` | Admin API 인증 Client ID |
| `KEYCLOAK_ADMIN_CLIENT_SECRET` | 조건부 | 없음 | Service Account 인증용 Client Secret |
| `KEYCLOAK_ADMIN_USERNAME` | 조건부 | 없음 | 사용자 인증 방식을 사용할 때 관리자 사용자명 |
| `KEYCLOAK_ADMIN_PASSWORD` | 조건부 | 없음 | 사용자 인증 방식을 사용할 때 관리자 비밀번호 |
| `KEYCLOAK_REALM_ENABLED` | 아니요 | `true` | 대상 Realm 활성화 여부 |
| `KEYCLOAK_REALM_DISPLAY_NAME` | 아니요 | 없음 | 대상 Realm 표시 이름 |
| `KEYCLOAK_CLIENT_PUBLIC` | 아니요 | `false` | 생성할 Client의 Public Client 여부 |
| `KEYCLOAK_CLIENT_REDIRECT_URIS` | 아니요 | 없음 | 쉼표로 구분된 Redirect URI 목록 |
| `KEYCLOAK_CLIENT_WEB_ORIGINS` | 아니요 | 없음 | 쉼표로 구분된 Web Origin 목록 |
| `KEYCLOAK_REALM_ROLES` | 아니요 | 없음 | 쉼표로 구분된 Realm Role 목록 |
| `KEYCLOAK_CLIENT_ROLES` | 아니요 | 없음 | 쉼표로 구분된 Client Role 목록 |

`KEYCLOAK_PROVISIONING_ENABLED=true`이면 Admin API 인증정보가 필요하다.
Service Account의 Client ID/Secret 방식 또는 관리자 사용자명/비밀번호 방식 중
하나만 사용한다. 프로비저닝 대상 Realm과 Client는 각각 `KEYCLOAK_REALM`과
`KEYCLOAK_CLIENT_ID`를 사용한다.

`KEYCLOAK_TOKEN_GRANT_TYPE=client_credentials`이면
`KEYCLOAK_CLIENT_ID`와 필요한 경우 `KEYCLOAK_CLIENT_SECRET`을 사용해 토큰을
가져온다. `KEYCLOAK_TOKEN_GRANT_TYPE=password`이면
`KEYCLOAK_TOKEN_USERNAME`, `KEYCLOAK_TOKEN_PASSWORD`가 추가로 필요하다.
Password Grant는 레거시 또는 제한된 내부 사용 사례에 한해 지원하며 운영
환경의 기본 방식으로 권장하지 않는다.

### 9.3 PostgreSQL

`POSTGRES_DSN`이 설정된 경우 개별 연결 환경변수보다 우선한다.

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `POSTGRES_DSN` | 조건부 | 없음 | PostgreSQL 연결 URI |
| `POSTGRES_HOST` | 조건부 | 없음 | 데이터베이스 호스트 |
| `POSTGRES_PORT` | 아니요 | `5432` | 데이터베이스 포트 |
| `POSTGRES_DB` | 조건부 | 없음 | 데이터베이스 이름 |
| `POSTGRES_USER` | 조건부 | 없음 | 사용자명 |
| `POSTGRES_PASSWORD` | 조건부 | 없음 | 비밀번호 |
| `POSTGRES_SSLMODE` | 아니요 | `prefer` | PostgreSQL SSL 모드 |
| `POSTGRES_CONNECT_TIMEOUT_SECONDS` | 아니요 | `10` | 데이터베이스 연결 제한 시간 |
| `POSTGRES_POOL_SIZE` | 아니요 | `5` | 기본 연결 풀 크기 |
| `POSTGRES_MAX_OVERFLOW` | 아니요 | `10` | 추가 허용 연결 수 |

### 9.4 MinIO

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `MINIO_ENDPOINT` | 예 | 없음 | `host:port` 형식의 Endpoint |
| `MINIO_ACCESS_KEY` | 예 | 없음 | Access Key |
| `MINIO_SECRET_KEY` | 예 | 없음 | Secret Key |
| `MINIO_SECURE` | 아니요 | `true` | HTTPS 사용 여부 |
| `MINIO_REGION` | 아니요 | 없음 | 저장소 Region |
| `MINIO_BUCKET` | 아니요 | 없음 | 기본 Bucket |
| `MINIO_REQUEST_TIMEOUT_SECONDS` | 아니요 | `30` | 객체 저장소 요청 제한 시간 |
| `MINIO_MAX_RETRIES` | 아니요 | `3` | 일시적 요청 오류 최대 재시도 횟수 |

### 9.5 Milvus

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `MILVUS_URI` | 예 | 없음 | Milvus 서버 URI |
| `MILVUS_TOKEN` | 조건부 | 없음 | 인증 토큰 |
| `MILVUS_DB_NAME` | 아니요 | `default` | 데이터베이스 이름 |
| `MILVUS_COLLECTION` | 아니요 | 없음 | 기본 Collection |
| `MILVUS_SECURE` | 아니요 | `false` | TLS 사용 여부 |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | 아니요 | `10` | Milvus 연결 제한 시간 |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | 아니요 | `30` | Milvus 작업 요청 제한 시간 |
| `MILVUS_MAX_RETRIES` | 아니요 | `3` | 일시적 연결 및 요청 오류 최대 재시도 횟수 |

### 9.6 Ollama

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `OLLAMA_HOST` | 예 | 없음 | Ollama API 기본 URL |
| `OLLAMA_GENERATION_MODEL` | 아니요 | 없음 | 기본 생성 모델 |
| `OLLAMA_EMBEDDING_MODEL` | 아니요 | 없음 | 기본 임베딩 모델 |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | 아니요 | `120` | 모델 호출 요청 제한 시간 |
| `OLLAMA_MAX_RETRIES` | 아니요 | `2` | 일시적 HTTP 오류 최대 재시도 횟수 |

### 9.7 Langfuse

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `LANGFUSE_HOST` | 예 | 없음 | Langfuse API 기본 URL |
| `LANGFUSE_PUBLIC_KEY` | 예 | 없음 | Public Key |
| `LANGFUSE_SECRET_KEY` | 예 | 없음 | Secret Key |
| `LANGFUSE_ENABLED` | 아니요 | `true` | 트레이싱 활성화 여부 |
| `LANGFUSE_RELEASE` | 아니요 | 없음 | 애플리케이션 릴리스 식별자 |
| `LANGFUSE_ENVIRONMENT` | 아니요 | `DOCMESH_ENV` 값 | Langfuse 환경 식별자 |
| `LANGFUSE_REQUEST_TIMEOUT_SECONDS` | 아니요 | `10` | Langfuse API 요청 제한 시간 |
| `LANGFUSE_MAX_RETRIES` | 아니요 | `3` | 일시적 전송 오류 최대 재시도 횟수 |

`LANGFUSE_ENABLED=false`인 경우 나머지 Langfuse 환경변수는 선택값으로
처리한다.

### 9.8 NATS

| 환경변수 | 필수 | 기본값 | 설명 |
| --- | --- | --- | --- |
| `NATS_SERVERS` | 예 | 없음 | 쉼표로 구분된 NATS 서버 URL 목록 |
| `NATS_USER` | 조건부 | 없음 | 사용자명 인증 사용 시 사용자명 |
| `NATS_PASSWORD` | 조건부 | 없음 | 사용자명 인증 사용 시 비밀번호 |
| `NATS_TOKEN` | 조건부 | 없음 | 토큰 인증 사용 시 토큰 |
| `NATS_CREDS_FILE` | 조건부 | 없음 | Credentials 파일 경로 |
| `NATS_NAME` | 아니요 | `docmesh-py-core` | 클라이언트 연결 이름 |
| `NATS_CONNECT_TIMEOUT_SECONDS` | 아니요 | `10` | 연결 제한 시간 |
| `NATS_MAX_RECONNECT_ATTEMPTS` | 아니요 | `10` | 최대 재연결 횟수 |

NATS 인증 방식은 사용자명/비밀번호, 토큰, Credentials 파일 중 하나만
선택하도록 검증한다.

## 10. 보안 요구사항

- 민감정보는 환경변수 또는 배포 플랫폼의 Secret 관리 기능으로 주입한다.
- `.env` 파일을 지원할 경우 실제 비밀정보가 포함된 파일은 버전 관리에서
  제외한다.
- 운영 환경에서는 TLS 사용 및 인증서 검증을 기본 정책으로 한다.
- SSL 검증 비활성화 설정은 개발 및 테스트 환경에서만 허용하는 정책을
  제공해야 한다.
- DSN 또는 URI를 오류 메시지에 표시할 때 사용자명, 비밀번호, 토큰,
  Query Parameter의 민감값을 마스킹해야 한다.
- 환경변수의 원문 값을 디버그 로그에 출력하지 않아야 한다.
- Keycloak 프로비저닝 계정에는 Realm, Client, Role 관리에 필요한 최소 권한만
  부여해야 한다.
- Keycloak 관리자 사용자명/비밀번호 방식보다 Service Account와 제한된
  Client 권한 사용을 권장한다.
- Access Token, ID Token, Refresh Token 원문은 애플리케이션 로그와 관측성
  이벤트에 기록하지 않아야 한다.
- 토큰 검증에 성공해도 사용자 클레임 전체를 무분별하게 로그로 남기지
  않아야 하며, 감사 목적에는 최소 필드만 선택적으로 기록해야 한다.
- Password Grant 사용 시 해당 설정이 운영 환경에서 기본값으로 활성화되지
  않도록 해야 한다.

## 11. 비기능 요구사항

### 성능

- 환경변수 파싱과 설정 객체 생성은 일반적인 실행 환경에서 100ms 이내를
  목표로 한다.
- 상태 확인은 서비스별로 독립 실행할 수 있어야 하며, 전체 확인 시 병렬
  수행을 지원하는 것을 권장한다.

### 안정성

- 개별 선택 서비스의 장애가 다른 서비스 클라이언트 생성에 영향을 주지
  않아야 한다.
- 연결과 종료를 반복해도 리소스 누수가 없어야 한다.
- PostgreSQL 연결 풀과 NATS 재연결 정책은 환경변수로 조정 가능해야 한다.

### 호환성

- Python 3.11 이상을 지원한다.
- 동기 또는 비동기 라이브러리의 특성에 맞는 인터페이스를 제공하되,
  애플리케이션 이벤트 루프를 임의로 생성하거나 종료하지 않아야 한다.

### 테스트 가능성

- 환경변수 입력을 격리하여 단위 테스트할 수 있어야 한다.
- 외부 서비스 없이 설정 검증과 오류 마스킹을 테스트할 수 있어야 한다.
- 실제 서비스 연동은 별도의 통합 테스트로 분리해야 한다.

## 12. 완료 기준

다음 조건을 모두 충족하면 v0.1.0의 외부 서비스 연결 기능이 완료된 것으로
판단한다.

1. 7개 외부 서비스의 설정 객체와 클라이언트 생성 인터페이스가 제공된다.
2. 명세된 필수 환경변수의 누락 및 잘못된 타입에 대한 테스트가 통과한다.
3. 서비스별 정상 연결과 대표적인 연결 실패에 대한 통합 테스트가 통과한다.
4. 로그 및 예외 메시지에 등록된 비밀번호, 토큰, Secret Key가 노출되지
   않는다는 테스트가 통과한다.
5. 모든 클라이언트에 연결 확인 및 필요한 경우 종료 기능이 제공된다.
6. 환경변수 예시 파일에 실제 비밀정보 없이 전체 설정 항목이 문서화된다.
7. CI에서 정적 검사, 단위 테스트, 민감정보 노출 검사가 통과한다.
8. Keycloak Realm, Client, Realm Role 및 Client Role의 최초 생성 테스트가
   통과한다.
9. 동일한 프로비저닝 설정을 반복 실행했을 때 추가 변경이 발생하지 않는
   멱등성 테스트가 통과한다.
10. Dry-run, 기존 리소스 갱신, 부분 실패 및 비밀정보 마스킹 테스트가
    통과한다.
11. Keycloak 토큰 획득 성공/실패와 민감정보 비노출 테스트가 통과한다.
12. 유효한 JWT에서 표준 사용자 정보와 역할이 올바르게 추출된다는 테스트가
    통과한다.
13. 만료 토큰, 잘못된 서명, Audience 불일치에 대한 검증 실패 테스트가
    통과한다.

## 13. 주요 위험 및 대응

| 위험 | 영향 | 대응 |
| --- | --- | --- |
| 서비스 SDK별 동기/비동기 방식 차이 | 공통 인터페이스 복잡도 증가 | 억지로 단일 호출 방식으로 통합하지 않고 수명주기와 오류 모델만 표준화 |
| URI에 포함된 인증정보 노출 | 보안 사고 | 중앙 마스킹 함수와 로그 필터 적용 |
| 시작 시 모든 서비스 연결 검사 | 시작 지연 및 연쇄 장애 | 필수/선택 서비스 구분과 병렬 상태 확인 지원 |
| SDK 버전별 설정 옵션 변경 | 호환성 문제 | 지원 버전 범위를 고정하고 업그레이드 시 통합 테스트 수행 |
| 잘못된 TLS 비활성화 | 중간자 공격 위험 | 운영 환경 검증 및 경고 또는 시작 실패 정책 적용 |
| 과도한 Keycloak 관리자 권한 | 인증 시스템 전체에 대한 변경 위험 | 최소 권한 Service Account와 프로비저닝 기능의 명시적 활성화 적용 |
| 잘못된 프로비저닝 설정 | 기존 인증 흐름 장애 | Dry-run, 멱등 갱신, 자동 삭제 금지 및 통합 테스트 적용 |
| 토큰 클레임 구조 해석 불일치 | 권한 오판 및 사용자 식별 오류 | 표준 사용자 정보 스키마 정의와 토큰 샘플 기반 테스트 적용 |
| 토큰 원문 또는 과도한 클레임 로깅 | 개인정보 및 인증정보 노출 | 토큰 마스킹 정책과 감사 로그 최소 필드 정책 적용 |

## 14. 향후 고려사항

- Secret Manager 또는 Vault 기반 설정 공급자 지원
- Kubernetes Readiness/Liveness Probe 연동
- OpenTelemetry 기반 공통 메트릭 및 트레이싱
- 서비스별 Circuit Breaker와 세부 재시도 정책
- 다중 테넌트 또는 다중 연결 프로파일 지원
