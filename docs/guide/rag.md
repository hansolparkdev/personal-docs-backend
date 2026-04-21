# RAG 파이프라인 상세

## RAG란 무엇인가

RAG(Retrieval-Augmented Generation, 검색 증강 생성)는 AI 언어 모델(LLM)이 답변을 생성할 때 미리 저장된 문서에서 관련 내용을 검색하여 근거로 활용하는 기술입니다.

일반 LLM은 학습 시점의 지식만 가지고 있어 사용자의 개인 문서나 최신 정보를 모릅니다. RAG는 이 문제를 해결합니다.

**RAG 없이**: "이 계약서의 위약금 조항은 무엇인가요?" → LLM이 모름

**RAG 사용 시**:
1. 계약서를 업로드하면 내용이 잘게 쪼개져 벡터 DB에 저장됩니다.
2. 질문이 들어오면 "위약금"과 관련된 계약서 부분을 검색합니다.
3. 검색된 내용을 LLM에 제공하면 LLM이 문서 기반으로 정확한 답변을 생성합니다.

---

## 이 시스템의 RAG 동작 방식 단계별 설명

### 1단계: 파일 업로드 → 색인 처리

파일을 업로드하면 백그라운드에서 자동으로 색인 처리가 이루어집니다.

```
파일 업로드 (POST /api/v1/files)
    |
    v
MinIO에 원본 파일 저장
    |
    v
[백그라운드 작업: index_file()]
    |
    +-- MinIO에서 파일 바이트 읽기
    |
    +-- MarkItDown으로 Markdown 텍스트로 변환
    |   (PDF, DOCX, PPTX, XLSX, MD, TXT 모두 통일된 텍스트로 변환)
    |
    +-- RecursiveCharacterTextSplitter로 청크 분할
    |   chunk_size=1000자, chunk_overlap=200자
    |   (청크 간 200자 중복으로 문맥 단절 방지)
    |
    +-- OpenAI text-embedding-3-small으로 각 청크를 1536차원 벡터로 변환
    |
    +-- file_chunks 테이블에 저장 (content + embedding + user_id + file_id)
    |
    +-- files.index_status = "indexed" 로 업데이트
```

### 2단계: 질문 → 유사도 검색 → 컨텍스트 구성

사용자가 챗에서 메시지를 전송하면 다음이 수행됩니다.

```
사용자 질문 수신
    |
    +-- 질문 텍스트를 OpenAI text-embedding-3-small으로 벡터화
    |   (query_embedding: 1536차원)
    |
    +-- 해당 유저의 모든 file_chunks 조회 (user_id 필터 적용)
    |
    +-- 코사인 유사도 계산 (query_embedding vs 각 chunk.embedding)
    |   유사도 = dot(a, b) / (norm(a) * norm(b))
    |
    +-- 유사도 내림차순 정렬 후 상위 5개 청크 선택 (K=5)
    |
    +-- 컨텍스트 구성:
        "[출처: {file_id}, 청크 {chunk_index}]\n{chunk_content}"
        형식으로 5개 청크를 합쳐 하나의 컨텍스트 문자열 생성
```

### 3단계: 히스토리 + 컨텍스트 → LLM → SSE 스트리밍 응답

```
컨텍스트 구성 완료
    |
    +-- 최근 대화 히스토리 조회 (최대 20개 메시지)
    |
    +-- LangChain 메시지 배열 구성:
    |   [
    |     SystemMessage("다음 문서를 참고하여 답변하세요:\n\n{context}"),
    |     HumanMessage(히스토리_유저_메시지1),
    |     AIMessage(히스토리_AI_메시지1),
    |     ...
    |     HumanMessage(현재_질문)
    |   ]
    |
    +-- ChatOpenAI (gpt-4o-mini, streaming=True)로 스트리밍 생성
    |
    +-- 생성된 토큰을 SSE 이벤트로 실시간 전송:
    |   event: token
    |   event: sources
    |   event: done
    |
    +-- 완성된 답변과 출처를 DB에 저장 (chat_messages 테이블)
```

---

## LangGraph StateGraph 구조 설명

현재 `rag_service.py`는 LangGraph StateGraph를 직접 사용하지 않고, 동일한 논리를 단일 비동기 제너레이터 함수(`stream_rag_response`)로 구현합니다. 흐름을 StateGraph 노드로 표현하면 다음과 같습니다.

```
[load_history 노드]
    state에 세션 제목 설정 (첫 메시지인 경우)
    user 메시지 DB에 저장
    최근 20개 메시지 히스토리 로드
        |
        v
[retrieve 노드]
    user_id로 file_chunks 조회
    query를 임베딩
    코사인 유사도로 상위 5개 청크 검색
    컨텍스트 문자열 구성
        |
        v
[generate 노드]
    System + History + Context + Query를 LLM에 전달
    토큰 단위로 SSE 스트리밍
    sources, done 이벤트 전송
    완성된 답변 DB 저장
```

---

## SSE 이벤트 형식

`POST /api/v1/chats/{session_id}/messages` 응답은 `text/event-stream` 형식의 SSE 스트림입니다.

### token 이벤트 (반복 발생)

LLM이 생성하는 토큰을 실시간으로 전송합니다.

```
event: token
data: {"text": "안"}

event: token
data: {"text": "녕"}

event: token
data: {"text": "하세요. 문서에 따르면..."}
```

### sources 이벤트 (1회 발생)

답변 생성에 사용된 문서 청크 출처 목록입니다.

```
event: sources
data: {"sources": [
  {"file_id": "123e4567-e89b-12d3-a456-426614174000", "filename": "", "chunk_index": 2},
  {"file_id": "123e4567-e89b-12d3-a456-426614174000", "filename": "", "chunk_index": 3},
  {"file_id": "234f5678-e89b-12d3-a456-426614174001", "filename": "", "chunk_index": 0}
]}
```

### done 이벤트 (1회 발생, 스트림 종료)

스트리밍이 정상 완료됨을 알립니다.

```
event: done
data: {}
```

### error 이벤트 (오류 발생 시)

LLM 호출 중 오류가 발생한 경우 전송됩니다.

```
event: error
data: {"message": "답변 생성 중 오류가 발생했습니다."}
```

### 문서 없음 폴백 (색인된 파일이 없는 경우)

유저가 파일을 업로드하지 않았거나 색인 완료된 파일이 없으면 폴백 메시지를 반환합니다.

```
event: token
data: {"text": "참고할 문서가 없습니다. 파일을 업로드하고 색인을 완료해 주세요."}

event: sources
data: {"sources": []}

event: done
data: {}
```

---

## pgvector 격리 설명 (user_id 필터)

각 유저는 자신이 업로드한 파일의 청크만 RAG 검색에 사용됩니다. `file_chunks` 테이블에는 `user_id` 컬럼이 있으며, `get_indexed_chunks()` 함수가 반드시 `user_id` 조건으로 필터링합니다.

```python
# file_service.py
async def get_indexed_chunks(db: AsyncSession, user_id: str) -> list[FileChunk]:
    result = await db.execute(
        select(FileChunk).where(FileChunk.user_id == user_id)  # 유저 격리 핵심
    )
    return list(result.scalars().all())
```

이를 통해 A 유저의 문서가 B 유저의 RAG 검색에 노출되지 않습니다.

---

## 임베딩 모델 스펙

| 항목 | 값 |
|---|---|
| 모델 | OpenAI text-embedding-3-small |
| 벡터 차원 | 1536 |
| 유사도 방식 | 코사인 유사도 |
| 청크 크기 | 1000자 |
| 청크 중복 | 200자 |
| 검색 K | 5 (상위 5개 청크) |
| LLM 모델 | OpenAI gpt-4o-mini |
| 히스토리 | 최근 20개 메시지 |
