# RAG 파이프라인 학습 가이드

> 대상: JavaScript 경험이 있는 Python/FastAPI 입문자
> 이 문서는 personal-docs 프로젝트의 RAG 챗 시스템을 예시로, 개념부터 구현까지 "왜"를 중심으로 설명합니다.

---

## 1. RAG란 무엇인가?

**RAG(Retrieval-Augmented Generation)** 는 "검색 보강 생성"입니다.

### 비유: 오픈북 시험

- 일반 LLM = 외운 것만 말하는 학생 (학습 데이터 안에 없으면 모름)
- RAG = 시험 중에 교재를 펼쳐보고 답을 쓰는 학생 (내 파일에서 관련 내용을 찾아서 답변)

```
사용자 질문
    │
    ▼
[내 파일에서 관련 내용 검색]  ← "Retrieval"
    │
    ▼
[LLM에게 관련 내용 + 질문 전달]  ← "Augmented"
    │
    ▼
[LLM이 근거 있는 답변 생성]  ← "Generation"
```

### 왜 RAG가 필요한가?

| 상황 | 일반 LLM | RAG |
|------|----------|-----|
| "내 회사 인사 규정이 뭐야?" | 모름 | 업로드한 PDF에서 찾아서 답변 |
| 최신 데이터 | 학습 날짜 이후 모름 | 내가 올린 파일 기준으로 답변 |
| 출처 확인 | 불투명 | 어느 파일 몇 페이지인지 표시 |

---

## 2. 전체 흐름 개요

RAG 시스템은 크게 두 단계로 나뉩니다.

```
[파일 업로드 파이프라인] — 1회성, 미리 준비
  파일 업로드 → 파싱 → 청킹 → 임베딩 → DB 저장

[질문-답변 파이프라인] — 매 질문마다 실행
  질문 → 임베딩 → 벡터 검색 → LLM → 스트리밍 응답
```

---

## 3. 파일 업로드 파이프라인

### 3-1. 파일 업로드 & 검증

```python
# app/api/v1/files.py
ext = os.path.splitext(file.filename or "")[1].lower()
if ext not in settings.allowed_extensions:
    raise HTTPException(status_code=415, ...)
```

**왜 MIME 타입이 아닌 확장자로 검증하나?**

MIME 타입은 클라이언트가 설정하는 값이라 신뢰할 수 없습니다. 확장자는 실제 파싱 라이브러리가 사용하는 기준과 일치합니다.

JavaScript 비교:
```javascript
// JS에서는 이렇게 할 수 있지만 서버 측에선 확장자가 더 안전
file.type === 'application/pdf'  // 클라이언트가 조작 가능
```

### 3-2. 파싱 (텍스트 추출)

파일을 그대로 LLM에 줄 수 없습니다. 텍스트로 변환해야 합니다.

```
PDF    → pypdf로 페이지별 텍스트 추출
PPTX   → MarkItDown으로 마크다운 변환 → 슬라이드별 분리
기타   → MarkItDown으로 마크다운 변환
```

**PPTX 슬라이드 번호 파싱 — 왜 필요한가?**

MarkItDown이 PPTX를 변환하면 슬라이드 구분자를 HTML 주석으로 삽입합니다:
```
<!-- Slide number: 1 -->
슬라이드 내용...
<!-- Slide number: 2 -->
또 다른 내용...
```

이 주석을 정규식으로 파싱해 슬라이드 단위로 분리하면, 나중에 "3번 슬라이드에서 찾았습니다"처럼 출처를 정확히 표시할 수 있습니다.

```python
_SLIDE_NUMBER_RE = re.compile(r"<!--\s*Slide number:\s*(\d+)\s*-->")
```

### 3-3. 청킹(Chunking)

**청크(Chunk)란?** 긴 문서를 LLM이 한 번에 처리할 수 있는 작은 조각으로 나눈 것입니다.

```
[긴 PDF 전체]  →  [청크1: 1000자] [청크2: 1000자] [청크3: 1000자] ...
```

**왜 청킹이 필요한가?**

- LLM은 한 번에 처리할 수 있는 텍스트 길이(컨텍스트 창)에 제한이 있습니다
- 100페이지 PDF를 전부 넣으면 비용이 폭증하고, 오히려 정확도가 떨어집니다
- 질문과 관련된 조각만 골라서 넣는 것이 핵심입니다

```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,   # 청크 최대 글자 수
    chunk_overlap=200  # 청크 간 겹치는 글자 수 (문맥 연속성 유지)
)
```

**chunk_overlap이 왜 필요한가?** 문장이 청크 경계에서 잘릴 수 있기 때문입니다. 200자 겹치게 하면 경계 부근의 내용이 양쪽 청크에 모두 포함됩니다.

### 3-4. 임베딩(Embedding)

**임베딩이란?** 텍스트를 숫자 벡터로 변환하는 것입니다.

```
"파이썬 비동기 처리"  →  [0.12, -0.34, 0.87, ..., 0.23]  (1536개 숫자)
"async/await 패턴"   →  [0.11, -0.31, 0.85, ..., 0.21]  (비슷한 벡터!)
"오늘 점심 메뉴"     →  [-0.52, 0.78, -0.14, ..., 0.66]  (전혀 다른 벡터)
```

의미가 비슷한 텍스트는 비슷한 벡터가 됩니다. 이것이 벡터 검색의 핵심 원리입니다.

JavaScript 비교:
```javascript
// JS에는 이런 개념이 없음. Python 생태계에서 OpenAI API 호출로 생성
const vector = await openai.embeddings.create({ input: text, model: "text-embedding-3-small" })
```

```python
# Python: 비동기로 모든 청크를 한 번에 임베딩 (배치 처리로 API 호출 최소화)
embeddings = await embeddings_model.aembed_documents(all_texts)
```

### 3-5. DB 저장

```
FileChunk 테이블
├── id (UUID)
├── file_id → File 테이블 참조
├── user_id
├── chunk_index (몇 번째 청크인지)
├── content (원본 텍스트)
├── embedding (Vector(1536)) ← pgvector 타입
└── page_number (PDF 페이지 or PPTX 슬라이드 번호)
```

---

## 4. 질문-답변 파이프라인

### 4-1. 질문 임베딩

사용자가 질문을 보내면, 그 질문도 동일한 임베딩 모델로 벡터로 변환합니다.

```python
query_embedding = await embeddings_model.aembed_query(search_query)
```

### 4-2. pgvector 벡터 검색

**유사도(Similarity)란?** 두 벡터가 얼마나 비슷한지를 나타내는 수치입니다.

**코사인 거리(Cosine Distance)란?**

두 벡터 사이의 각도를 측정합니다. 방향이 같으면 거리 = 0, 방향이 반대면 거리 = 2입니다.

```
질문 벡터 →  [0.12, -0.34, 0.87]
청크A 벡터 → [0.11, -0.31, 0.85]  코사인 거리 = 0.02  (매우 유사!)
청크B 벡터 → [-0.52, 0.78, -0.14] 코사인 거리 = 1.83  (전혀 다름)
```

**`<=>` 연산자**는 pgvector 확장이 제공하는 코사인 거리 연산자입니다.

```python
# app/services/file_service.py
distance = cast(FileChunk.embedding.op("<=>")(query_embedding), Float).label("distance")
stmt = (
    select(FileChunk, distance)
    .join(File, FileChunk.file_id == File.id)
    .where(
        File.user_id == user_id,
        File.deleted_at.is_(None),       # 삭제된 파일 제외
        distance < distance_threshold,   # 임계값 필터
    )
    .order_by(distance)  # 가장 유사한 것부터
    .limit(5)
)
```

**왜 numpy 대신 pgvector를 쓰나?**

| 방법 | 과정 | 문제 |
|------|------|------|
| numpy (기존) | 모든 청크 메모리 로드 → Python에서 계산 | 청크 수가 늘면 메모리/속도 선형 증가 |
| pgvector (개선) | DB에서 인덱스 활용해 직접 검색 | 수백만 청크도 빠르게 처리 |

**`cast(..., Float)` — 왜 필요한가?**

pgvector의 `<=>` 연산자 결과값은 SQLAlchemy가 Python 타입으로 자동 인식하지 못합니다. `cast`로 명시적으로 Float 타입임을 알려줘야 `distance < threshold` 같은 비교 연산이 동작합니다.

```python
from sqlalchemy import Float
from sqlalchemy.sql.expression import cast

distance = cast(FileChunk.embedding.op("<=>")(query_embedding), Float).label("distance")
```

### 4-3. 유사도 임계값

```python
rag_similarity_threshold = 0.75  # settings에서 설정
```

거리값이 0.75 초과인 청크는 "관련 없는 문서"로 판단해 제외합니다. 이를 통해 전혀 관계없는 문서 내용이 답변에 포함되는 것을 방지합니다.

---

## 5. 히스토리 중복 버그

### 문제: 잘못된 순서

```python
# 버그 버전 (잘못된 순서)
await save_user_message(...)    # 1. 먼저 저장
messages = await get_history()  # 2. 조회하면 현재 질문이 포함됨!
# LLM에게: [과거 질문들... + 현재 질문] + 현재 질문  ← 현재 질문이 2번!
```

### 해결: 순서 변경

```python
# 수정 버전 (올바른 순서)
messages = await get_recent_messages(...)  # 1. 먼저 히스토리 조회 (현재 질문 없음)
# LLM 호출...
await save_user_message(...)               # 2. 스트리밍 완료 후 저장
await save_assistant_message(...)          # 3. AI 응답 저장
```

**왜 중요한가?** LLM에게 같은 질문이 중복으로 전달되면 혼란스러운 답변이 나오거나 불필요한 토큰(비용)이 낭비됩니다.

---

## 6. 맥락 의존 질문 처리

"더 말해봐", "계속", "이어서" 같은 짧은 질문은 단독으로는 검색이 안 됩니다.

```python
_CONTINUATION_PATTERNS = ["더 말해", "계속", "이어서", "추가로"]
_is_continuation = any(p in query for p in _CONTINUATION_PATTERNS)

search_query = query
if _is_continuation and messages:
    last_user_msg = next(
        (m for m in reversed(messages) if m.role == "user"), None
    )
    if last_user_msg:
        search_query = f"{last_user_msg.content} {query}"
```

**중요:** 이는 벡터 검색 쿼리에만 적용됩니다. LLM에 전달하는 히스토리는 그대로입니다. LLM은 이미 대화 맥락을 알고 있기 때문입니다.

---

## 7. SSE(Server-Sent Events) 스트리밍

**SSE란?** 서버에서 클라이언트로 데이터를 실시간으로 밀어넣는 방식입니다.

JavaScript 비교:
```javascript
// 클라이언트 (JS)
const es = new EventSource('/chats/session-id/messages')
es.addEventListener('token', (e) => {
    const { text } = JSON.parse(e.data)
    appendText(text)  // 글자가 하나씩 표시
})
es.addEventListener('sources', (e) => {
    const { sources } = JSON.parse(e.data)
    showSources(sources)
})
```

```python
# 서버 (Python) — AsyncGenerator로 이벤트를 하나씩 yield
async def stream_rag_response(...) -> AsyncGenerator[str, None]:
    async for chunk_token in llm.astream(lc_messages):
        text = chunk_token.content
        if text:
            yield f"event: token\ndata: {json.dumps({'text': text})}\n\n"

    yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
    yield "event: done\ndata: {}\n\n"
```

### SSE 이벤트 순서

```
event: token       ← LLM이 토큰을 생성할 때마다 (수십~수백 번)
data: {"text": "파"}

event: token
data: {"text": "이"}

event: sources     ← 스트리밍 완료 후 1회
data: {"sources": [...]}

event: done        ← 종료 신호
data: {}
```

### DB 커넥션 누수 문제와 해결

**문제:** FastAPI의 `Depends(get_db)`는 라우터 함수가 반환될 때 DB 세션을 닫습니다. 그런데 `StreamingResponse`는 라우터 함수가 반환된 후에도 데이터를 계속 전송합니다.

```python
# 문제: stream_db가 StreamingResponse 반환 전에 닫힘
@router.post("/{session_id}/messages")
async def send_message(db: AsyncSession = Depends(get_db)):  # 이 db는 일찍 닫힘
    return StreamingResponse(_stream_with_dependency_db())   # 스트리밍은 나중에...
```

**해결:** 스트리밍 전용 DB 세션을 별도로 생성합니다.

```python
# app/api/v1/chat.py
from app.db.base import AsyncSessionLocal

async def _stream_with_own_session():
    async with AsyncSessionLocal() as stream_db:  # 자체 세션 관리
        async for event in stream_rag_response(stream_db, ...):
            yield event

return StreamingResponse(_stream_with_own_session(), ...)
```

Python의 `async with`는 JavaScript의 `try/finally`와 유사합니다:
```javascript
// JS 비교
const client = await pool.connect()
try {
    // 작업
} finally {
    client.release()  // 반드시 해제
}
```

```python
# Python
async with AsyncSessionLocal() as stream_db:
    # 작업
    pass  # 블록 종료 시 자동으로 세션 닫힘 (__aexit__ 호출)
```

---

## 8. 핵심 Python 문법 정리

### AsyncGenerator

```python
from typing import AsyncGenerator

async def stream_rag_response(...) -> AsyncGenerator[str, None]:
    yield "첫 번째 데이터"
    await asyncio.sleep(0)
    yield "두 번째 데이터"
```

JavaScript 비교:
```javascript
async function* streamRagResponse() {
    yield "첫 번째 데이터"
    yield "두 번째 데이터"
}
```

### async with (비동기 컨텍스트 매니저)

```python
async with AsyncSessionLocal() as db:
    # db 사용
    pass  # 자동으로 db.close() 호출
```

### next() + reversed()

```python
# 히스토리에서 마지막 유저 메시지 찾기
last_user_msg = next(
    (m for m in reversed(messages) if m.role == "user"),
    None  # 없으면 None 반환
)
```

JavaScript 비교:
```javascript
const lastUserMsg = [...messages].reverse().find(m => m.role === 'user') ?? null
```

---

## 9. 용어 정리

| 용어 | 설명 | 비유 |
|------|------|------|
| 임베딩(Embedding) | 텍스트를 숫자 벡터로 변환 | 텍스트의 "좌표" |
| 청크(Chunk) | 문서를 나눈 작은 조각 | 책의 단락 |
| 코사인 거리 | 두 벡터 사이의 각도 기반 거리 | 방향이 같을수록 0에 가까움 |
| pgvector | PostgreSQL 벡터 검색 확장 | DB 내장 검색 엔진 |
| `<=>` 연산자 | pgvector 코사인 거리 연산자 | SQL에서 `distance(a, b)` |
| RAG | 검색 보강 생성 | 오픈북 시험 |
| SSE | 서버에서 클라이언트로 실시간 데이터 스트리밍 | 라디오 방송 |
| AsyncGenerator | 비동기 데이터를 순차적으로 yield하는 함수 | 비동기 이터레이터 |
| 유사도 임계값 | 관련 없는 문서를 거르는 거리 기준값 | 검색 필터 |
