---
title: MinIO
created: 2026-06-10
updated: 2026-06-10
type: entity
tags: [service-connection]
sources: []
confidence: high
---

# MinIO

S3 호환 오브젝트 스토리지. 헬스체크는 `list_buckets()`.

## 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `MINIO_ENDPOINT` | ✅ | - | 호스트:포트 |
| `MINIO_ACCESS_KEY` | ✅ | - | 액세스 키 |
| `MINIO_SECRET_KEY` | ✅ | - | 시크릿 키 |
| `MINIO_SECURE` | - | `true` | HTTPS 사용 여부 |
| `MINIO_REGION` | - | - | 리전 |
| `MINIO_BUCKET` | - | - | 기본 버킷명 |

> Production에서 `MINIO_SECURE=false`는 `ConfigError` 발생. ([[settings-system]] 참조)

## 관련 개념

- [[service-factory-registry]] — Minio 클라이언트 생성
- [[settings-system]] — `MinioConfig`
