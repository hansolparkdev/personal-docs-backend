## ADDED Requirements

### Requirement: 메시지 전송 및 SSE 스트리밍

인증된 사용자가 특정 세션에 메시지를 전송하면, 서버는 해당 사용자의 색인 완료 문서를 기반으로 RAG 파이프라인을 실행하고 답변을 SSE 스트리밍으로 반환한다.

SSE 이벤트 형식:
```
event: token
data: {"text": "답변 토큰"}

event: sources
data: {"sources": [{"file_id": "...", "filename": "...", "chunk_index": 0}]}

event: done
data: {}
```

#### Scenario 1: 정상 스트리밍 응답

- **Given** 유효한 JWT, 본인 소유 세션, 색인 완료 파일 1개 이상 존재
- **When** `POST /api/v1/chats/{session_id}/messages` body: `{"content": "질문 내용"}`
- **Then** `Content-Type: text/event-stream` 응답 스트림 개시
- **And** `event: token` 이벤트가 1개 이상 순차 전송됨
- **And** 모든 token 이벤트 이후 `event: sources` 이벤트 1회 전송
- **And** sources 이벤트 이후 `event: done` 이벤트 전송
- **And** 스트림 종료 후 DB에 user 메시지(role=user) 저장
- **And** 스트림 종료 후 DB에 assistant 메시지(role=assistant, content=전체 답변, sources=출처 목록 JSONB) 저장

#### Scenario 2: 타인 세션에 메시지 전송 시도

- **Given** 유효한 JWT, 타인 소유 session_id
- **When** `POST /api/v1/chats/{session_id}/messages` 요청
- **Then** HTTP 404 (스트림 미개시)

#### Scenario 3: 존재하지 않는 세션에 메시지 전송

- **Given** 유효한 JWT, 존재하지 않는 session_id
- **When** `POST /api/v1/chats/{session_id}/messages` 요청
- **Then** HTTP 404

#### Scenario 4: 미인증 요청

- **Given** JWT 없음 또는 만료된 JWT
- **When** `POST /api/v1/chats/{session_id}/messages` 요청
- **Then** HTTP 401

---

### Requirement: 색인 청크 없음 시 안내 응답

사용자에게 색인 완료 파일이 없는 경우, LLM을 호출하지 않고 참고할 문서가 없다는 안내를 스트리밍으로 반환한다.

#### Scenario 1: 색인 완료 파일 없음

- **Given** 유효한 JWT, 본인 소유 세션, 색인 완료 파일 0개
- **When** `POST /api/v1/chats/{session_id}/messages` 요청
- **Then** `Content-Type: text/event-stream` 응답 스트림 개시
- **And** `event: token` 이벤트로 "참고할 문서가 없습니다. 파일을 업로드하고 색인을 완료해 주세요." 안내 메시지 전송
- **And** `event: sources` 이벤트 전송 (sources 빈 배열)
- **And** `event: done` 이벤트 전송
- **And** DB에 user 메시지 저장
- **And** DB에 assistant 메시지(안내 문구, sources=[]) 저장

---

### Requirement: 대화 이력 반영

같은 세션의 직전 대화 맥락(최근 10턴 = 최대 20개 메시지)이 RAG 파이프라인의 LLM 프롬프트에 반영된다.

#### Scenario 1: 이전 대화 맥락 반영

- **Given** 유효한 JWT, 이미 4개 메시지(user 2 + assistant 2)가 있는 세션
- **When** 해당 세션에 새 메시지 전송
- **Then** LLM 프롬프트 구성 시 기존 4개 메시지가 이력으로 포함됨
- **And** 새 질문의 답변이 직전 맥락을 참고한 결과로 생성됨

#### Scenario 2: 10턴 초과 시 슬라이딩 윈도우

- **Given** 유효한 JWT, 24개 메시지(user 12 + assistant 12)가 있는 세션
- **When** 해당 세션에 새 메시지 전송
- **Then** LLM 프롬프트에는 최근 20개 메시지만 포함 (오래된 4개 제외)

---

### Requirement: pgvector 유저 격리 검색

RAG 파이프라인의 벡터 검색은 반드시 `user_id` 필터를 포함하여 다른 사용자의 청크가 검색되지 않도록 한다.

#### Scenario 1: 본인 청크만 검색 대상

- **Given** 사용자 A와 사용자 B 각각 색인 완료 파일 보유
- **When** 사용자 A가 메시지 전송
- **Then** pgvector 검색 쿼리에 `user_id = A` 필터 포함
- **And** 검색 결과에 사용자 B의 청크 미포함

#### Scenario 2: K=5 상위 청크 검색

- **Given** 유효한 JWT, 색인 완료 청크 20개 보유
- **When** 메시지 전송
- **Then** 의미적으로 가장 유사한 상위 5개 청크만 컨텍스트로 사용

---

### Requirement: 스트리밍 중단 시 부분 답변 폐기

스트리밍 도중 클라이언트 연결이 끊기면 부분 답변을 DB에 저장하지 않는다.

#### Scenario 1: 클라이언트 연결 끊김

- **Given** 스트리밍 진행 중 (token 이벤트 전송 중)
- **When** 클라이언트가 연결을 끊음
- **Then** 서버가 생성 중단 감지
- **And** 부분 assistant 메시지 DB 미저장
- **And** user 메시지는 이미 저장된 경우 그대로 유지

---

### Requirement: 스트리밍 시작 후 LLM 오류 처리

스트리밍이 시작된 이후 LLM 호출에서 예외가 발생하면 `event: error` 이벤트를 전송하고 부분 답변을 폐기한다.

#### Scenario 1: LLM 호출 실패 (스트리밍 시작 후)

- **Given** 스트리밍이 이미 시작되어 token 이벤트가 일부 전송된 상태
- **When** LLM 호출에서 예외 발생
- **Then** `event: error` 이벤트 전송 (`data: {"message": "답변 생성 중 오류가 발생했습니다."}`)
- **And** 부분 assistant 메시지 DB 미저장

#### Scenario 2: LLM 호출 실패 (스트리밍 시작 전)

- **Given** RAG 파이프라인 실행 전 (스트림 미개시)
- **When** LLM 호출 또는 파이프라인 준비 단계에서 예외 발생
- **Then** HTTP 500 응답 (스트림 미개시)

---

### Requirement: 출처 메타데이터 제공

스트리밍 응답의 `event: sources` 이벤트에는 답변 생성에 사용된 청크의 파일 식별자, 파일명, 청크 위치가 포함된다.

#### Scenario 1: 정상 출처 제공

- **Given** pgvector 검색으로 3개 청크가 사용된 경우
- **When** 스트리밍 완료 시점의 sources 이벤트
- **Then** `sources` 배열에 3개 항목 포함
- **And** 각 항목에 `file_id`, `filename`, `chunk_index` 필드 포함

#### Scenario 2: 색인 청크 없어 출처가 비어있는 경우

- **Given** 색인 완료 파일 없음으로 fallback 응답 처리된 경우
- **When** sources 이벤트 전송
- **Then** `sources` 배열이 빈 배열 `[]`
