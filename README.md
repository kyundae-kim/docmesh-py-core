# docmesh-py-core

DocMesh 프로젝트의 Python 기반 외부 서비스 연결 코어입니다.

## 포함 내용
- 환경변수 기반 설정 로딩 (`pydantic-settings`)
- Keycloak / PostgreSQL / MinIO / Milvus / Ollama / Langfuse / NATS 설정 모델
- 민감정보 마스킹 유틸리티
- 서비스 팩토리 레지스트리
- 헬스체크 집계
- Keycloak 프로비저닝 결과 모델

## 빠른 시작
1. 예시 환경변수 파일을 복사합니다.
   ```bash
   cp .env.example .env
   ```
2. `.env`에 실제 접속정보와 비밀값을 채웁니다.
3. 애플리케이션에서 설정을 로드합니다.

```python
from docmesh_py_core.config import Settings, load_settings

# 실제 프로세스 환경변수에서 직접 로드
settings = Settings()

# 또는 특정 매핑(dict)에서 로드
settings = load_settings({
    "KEYCLOAK_URL": "https://keycloak.example.com",
    "KEYCLOAK_REALM": "docmesh",
    "KEYCLOAK_CLIENT_ID": "docmesh-backend",
    "POSTGRES_DSN": "postgresql://user:***@db.example.com:5432/app",
    "MINIO_ENDPOINT": "minio.example.com:9000",
    "MINIO_ACCESS_KEY": "minio-access-key",
    "MINIO_SECRET_KEY": "secret",
    "MILVUS_URI": "http://milvus.example.com:19530",
    "OLLAMA_HOST": "http://ollama.example.com:11434",
    "LANGFUSE_HOST": "https://langfuse.example.com",
    "LANGFUSE_PUBLIC_KEY": "public-key",
    "LANGFUSE_SECRET_KEY": "secret-key",
    "NATS_SERVERS": "nats://n1.example.com:4222,nats://n2.example.com:4222",
})
```

## 환경변수 원칙
- 서비스별 `env_prefix`를 사용합니다.
  - `KEYCLOAK_*`, `POSTGRES_*`, `MINIO_*`, `MILVUS_*`, `OLLAMA_*`, `LANGFUSE_*`, `NATS_*`
- 공백 문자열은 비어 있는 값으로 처리됩니다.
- boolean은 `true` / `false`만 허용합니다.
- 리스트형 값은 쉼표 구분 문자열로 입력합니다.
- 운영 환경(`DOCMESH_ENV=production|prod`)에서는 일부 비보안 설정이 거부됩니다.

## 테스트
```bash
pytest -q test_docmesh_py_core
```

## 문서
- [설정 가이드](docs/config.md)
- [테스트 가이드](docs/test.md)
