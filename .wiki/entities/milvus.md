---
title: Milvus
created: 2026-06-10
updated: 2026-06-10
type: entity
tags: [service-connection]
sources: [raw/articles/prd.md, raw/project-docs/config.md]
confidence: high
---

# Milvus

벡터 데이터베이스. 임베딩 저장 및 유사도 검색에 활용. 헬스체크는 `list_collections()`.

## 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `MILVUS_URI` | ✅ | - | 연결 URI |
| `MILVUS_TOKEN` | - | - | 인증 토큰 |
| `MILVUS_DB_NAME` | - | `default` | 데이터베이스명 |
| `MILVUS_COLLECTION` | - | - | 기본 컬렉션명 |
| `MILVUS_SECURE` | - | `false` | TLS 사용 여부 |
| `MILVUS_CONNECT_TIMEOUT_SECONDS` | - | `10` | 연결 제한 시간 |
| `MILVUS_REQUEST_TIMEOUT_SECONDS` | - | `30` | 요청 제한 시간 |
| `MILVUS_MAX_RETRIES` | - | `3` | 일시적 연결/요청 오류 최대 재시도 횟수 |

> Production에서 `MILVUS_SECURE=false`는 `ConfigError` 발생. ([[settings-system]] 참조)

## 관련 개념

- [[service-factory-registry]] — MilvusClient 생성
- [[settings-system]] — `MilvusConfig`
