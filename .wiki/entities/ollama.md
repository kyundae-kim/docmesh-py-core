---
title: Ollama
created: 2026-06-10
updated: 2026-06-10
type: entity
tags: [service-connection]
sources: []
confidence: high
---

# Ollama

로컬 LLM 추론 서버. 임베딩 생성 및 텍스트 생성에 활용. 헬스체크는 `ps()`(실행 중 모델 목록).

## 환경 변수

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `OLLAMA_HOST` | ✅ | - | 서버 URL (e.g., `http://localhost:11434`) |
| `OLLAMA_GENERATION_MODEL` | - | - | 텍스트 생성 모델명 |
| `OLLAMA_EMBEDDING_MODEL` | - | - | 임베딩 모델명 |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | - | `120` | 요청 타임아웃 (생성이 오래 걸릴 수 있음) |

## 관련 개념

- [[service-factory-registry]] — OllamaClient 생성
- [[settings-system]] — `OllamaConfig`
