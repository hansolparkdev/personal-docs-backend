# RAG 챗 시스템 개발 리뷰

> 내가 올린 파일을 AI가 읽고 답변하는 시스템을 어떻게 만들었는가

---

## 1. 이걸 왜 만들었나

LLM(GPT 등)은 **학습된 데이터만 알아요.**

내가 오늘 작성한 문서, 내 경력기술서, 회사 내부 자료 — 이런 건 GPT가 모릅니다.

그래서 나온 개념이 **RAG (Retrieval-Augmented Generation)** 입니다.

```
일반 LLM:
  질문 → GPT → 답변 (자기가 아는 것만)

RAG:
  질문 → 내 문서에서 관련 내용 검색 → GPT → 답변 (내 문서 기반)
```

쉽게 말하면 **"오픈북 시험"** 입니다.
GPT한테 시험 문제와 함께 교재 일부를 펼쳐서 줍니다.

---

## 2. 전체 구조

```
[파일 업로드]
사용자 → 파일 업로드 → MinIO 저장
                     → 텍스트 추출 → 청킹 → 임베딩 → PostgreSQL 저장

[챗]
사용자 질문 → 질문 임베딩 → pgvector 유사도 검색 → 관련 청크 5개
                                                  → GPT에게 전달
                                                  → 스트리밍 답변
```

기술 스택:

| 역할 | 기술 |
|---|---|
| API 서버 | FastAPI (Python, 비동기) |
| 파일 저장 | MinIO (S3 호환) |
| DB + 벡터 검색 | PostgreSQL + pgvector |
| 파일 파싱 | pypdf (PDF), MarkItDown (PPTX/DOCX 등) |
| 임베딩 | OpenAI text-embedding-3-small |
| LLM | OpenAI gpt-4o-mini |
| LLM 연동 | LangChain |
| 인증 | Keycloak (OAuth2 / JWT) |

---

## 3. 파일 업로드 파이프라인

파일을 올리면 백그라운드에서 4단계 처리가 일어납니다.

```
① 파싱 — 파일을 텍스트로 변환
② 청킹 — 텍스트를 1000자씩 자름
③ 임베딩 — 각 청크를 1536개 숫자 배열로 변환
④ 저장 — DB에 텍스트 + 벡터 같이 저장
```

### ① 파싱

```python
# PDF → pypdf로 페이지 단위 추출
reader = PdfReader(io.BytesIO(content))
for i, page in enumerate(reader.pages, start=1):
    text = page.extract_text()
    pages.append((i, text))  # (페이지번호, 텍스트)

# PPTX → MarkItDown으로 변환 후 슬라이드 번호 주석 파싱
# MarkItDown이 변환 시 "<!-- Slide number: 3 -->" 형태로 삽입
_SLIDE_NUMBER_RE = re.compile(r"<!--\s*Slide number:\s*(\d+)\s*-->")
parts = _SLIDE_NUMBER_RE.split(markdown_text)
# → 슬라이드 단위로 분리 후 각각 (슬라이드번호, 텍스트) 저장
```

**왜 슬라이드 단위로 나누나?**
나중에 "이 답변은 몇 페이지에서 왔는지" 를 알려주기 위해서입니다.

### ② 청킹 (Chunk)

**청킹이란?** 텍스트를 일정 크기로 자르는 것.

왜 자르나? LLM에 파일 전체를 넣을 수 없기 때문입니다.
- GPT는 한 번에 처리할 수 있는 텍스트 양이 제한됩니다 (토큰 한도)
- 관련 없는 내용까지 다 넣으면 답변 품질이 떨어집니다

```python
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,    # 1000자씩 자름
    chunk_overlap=200,  # 앞뒤 200자 겹치게
)
chunks = splitter.split_text(page_text)
```

**overlap(겹침)이 있는 이유:**
중요한 문장이 청크 경계에서 잘릴 수 있어서 앞뒤로 200자씩 겹쳐 문맥을 유지합니다.

### ③ 임베딩 (Embedding)

**임베딩이란?** 텍스트를 숫자 배열(벡터)로 변환하는 것.

```
"Python은 인기있는 언어입니다"  →  [0.12, -0.34, 0.89, ...]  (1536개 숫자)
"파이썬은 유명한 프로그래밍 언어" →  [0.11, -0.31, 0.91, ...]  (비슷한 숫자)
"오늘 점심은 삼겹살"            →  [-0.54, 0.77, -0.12, ...]  (전혀 다른 숫자)
```

**비슷한 의미 = 비슷한 숫자 배열.** OpenAI 임베딩 모델이 의미를 학습해서 변환해줍니다.

1536차원? → OpenAI text-embedding-3-small 모델의 출력 크기. 텍스트의 의미를 1536개 숫자로 압축한 것.

```python
# 모든 청크를 한 번에 배치로 요청 (API 호출 횟수 최소화)
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
embeddings = await embeddings_model.aembed_documents(all_texts)
# → [청크0 벡터, 청크1 벡터, 청크2 벡터, ...]
```

### ④ DB 저장

```python
# file_chunks 테이블
FileChunk(
    file_id=...,
    user_id=...,
    chunk_index=0,
    content="Python은 인기있는 언어입니다...",  # 원본 텍스트
    embedding=[0.12, -0.34, 0.89, ...],          # 1536개 벡터
    page_number=3,                                # PDF 페이지 or PPTX 슬라이드
)
```

**content와 embedding을 같이 저장하는 이유:**
- **검색은 embedding으로** (벡터 유사도 비교)
- **GPT에게 전달은 content로** (사람이 읽는 텍스트)

---

## 4. 챗 파이프라인

질문이 들어오면 7단계로 처리됩니다.

```
질문 입력
  ↓
① 히스토리 조회 (이전 대화)
  ↓
② 질문 임베딩 → 벡터 변환
  ↓
③ pgvector 유사도 검색 → 관련 청크 5개
  ↓
④ 프롬프트 구성 (청크 내용 + 히스토리 + 질문)
  ↓
⑤ GPT 스트리밍 호출
  ↓
⑥ SSE로 토큰 실시간 전송
  ↓
⑦ DB 저장 (user 메시지 → assistant 메시지)
```

---

## 5. 유사도 검색 — 핵심 개념

### 유사도란?

두 벡터가 **얼마나 같은 방향을 가리키는지** 측정하는 것.

```
"Python 언어 관련" 질문 벡터:  ↗ (이 방향)
"파이썬 프로그래밍 소개" 벡터:  ↗ (거의 같은 방향)  → 유사도 높음
"오늘 날씨 맑음" 벡터:          ↙ (완전 다른 방향)  → 유사도 낮음
```

### 코사인 거리 (Cosine Distance)

두 벡터 사이의 각도를 거리로 표현한 것.

```
거리 0.0 = 완전히 같은 방향 (동일한 의미)
거리 0.5 = 어느 정도 다름
거리 1.0 = 직각 (전혀 무관)
거리 2.0 = 반대 방향 (반대 의미)
```

**임계값 0.75를 쓰는 이유:**
- 거리 0~0.75 → 관련 있는 문서 → 프롬프트에 포함
- 거리 0.75 초과 → 관련 없는 문서 → 제외
- 실제 측정: 관련 있는 문서는 0.6~0.74, 없는 문서는 0.8 이상

### pgvector `<=>` 연산자

PostgreSQL에 pgvector 확장을 설치하면 DB가 직접 벡터 연산을 합니다.

```python
# app/services/file_service.py
distance = cast(
    FileChunk.embedding.op("<=>")(query_embedding),
    Float
).label("distance")

stmt = (
    select(FileChunk, distance)
    .join(File, FileChunk.file_id == File.id)
    .where(
        File.user_id == user_id,          # 내 파일만
        File.deleted_at.is_(None),        # 삭제 안 된 파일만
        FileChunk.embedding.isnot(None),  # 임베딩 있는 것만
        distance < 0.75,                  # 임계값 이하만
    )
    .order_by(distance)   # 가장 유사한 순
    .limit(5)             # 상위 5개만
)
```

**기존 방식(numpy)과 비교:**

| | numpy 방식 | pgvector 방식 |
|---|---|---|
| 동작 | 전체 청크를 Python 메모리에 로드 후 하나씩 계산 | DB 안에서 계산, 상위 5개만 반환 |
| 청크 10만 개 | ~600MB 메모리, 느림 | 메모리 거의 없음, 빠름 |
| 코드 | `_cosine_sim()` 함수 직접 구현 | `<=>` 연산자 한 줄 |

---

## 6. LangChain이 하는 역할

LangChain은 LLM을 쓸 때 반복되는 작업들을 미리 만들어둔 **도구 모음**입니다.

이 프로젝트에서 쓰는 것:

```python
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import SystemMessage, HumanMessage, AIMessage

# 임베딩 모델 래퍼
embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
query_vector = await embeddings_model.aembed_query("질문 텍스트")

# LLM 래퍼 (스트리밍)
llm = ChatOpenAI(model="gpt-4o-mini", streaming=True)

# 메시지 형식
messages = [
    SystemMessage(content="다음 문서를 참고하여 답변하세요:\n\n{청크 내용}"),
    HumanMessage(content="이전 질문"),   # 히스토리
    AIMessage(content="이전 답변"),      # 히스토리
    HumanMessage(content="현재 질문"),
]

# 스트리밍 호출
async for token in llm.astream(messages):
    yield token.content  # 토큰 단위로 실시간 전송
```

LangChain 없이도 구현할 수 있지만, OpenAI API 호출/재시도/형식 변환 등을 대신 처리해줍니다.

---

## 7. SSE 스트리밍

**SSE(Server-Sent Events)** = 서버가 클라이언트로 실시간 데이터를 밀어주는 방식.

챗GPT처럼 글자가 실시간으로 나오는 것이 이 방식입니다.

```python
# 응답 형식
"event: token\ndata: {\"text\": \"안\"}\n\n"
"event: token\ndata: {\"text\": \"녕\"}\n\n"
"event: token\ndata: {\"text\": \"하\"}\n\n"
"event: sources\ndata: {\"sources\": [{\"filename\": \"경력기술서.pptx\", \"page_number\": 3}]}\n\n"
"event: done\ndata: {}\n\n"
```

```python
# Python generator로 구현
async def stream_rag_response(...) -> AsyncGenerator[str, None]:
    async for token in llm.astream(messages):
        yield f"event: token\ndata: {json.dumps({'text': token.content})}\n\n"

    yield f"event: sources\ndata: {json.dumps({'sources': sources})}\n\n"
    yield "event: done\ndata: {}\n\n"
```

**AsyncGenerator란?**
`yield` 로 값을 하나씩 내보내는 함수입니다. `async for` 로 받을 수 있습니다.

---

## 8. 개발 중 만난 문제들

### 문제 1: DB 커넥션 누수

**증상:**
```
The garbage collector is trying to clean up non-checked-in connection
```

**원인:**
FastAPI의 `Depends(get_db)` 는 라우터 함수가 끝나면 세션을 닫습니다.
근데 `StreamingResponse` 는 라우터 함수 반환 이후에도 계속 실행됩니다.
→ 이미 닫힌 DB 세션으로 쿼리를 시도

```python
# 문제 있는 코드
@router.post("/{session_id}/messages")
async def send_message(
    db: AsyncSession = Depends(get_db),  # ← 함수 반환 시 세션 닫힘
):
    return StreamingResponse(
        stream_rag_response(db, ...),  # ← 스트리밍 중 db 사용하려는데 이미 닫힘
    )
```

**해결:**
스트리밍 전용 DB 세션을 별도로 생성

```python
async def _stream_with_own_session():
    async with AsyncSessionLocal() as stream_db:  # 스트리밍 동안 살아있음
        async for event in stream_rag_response(stream_db, ...):
            yield event

return StreamingResponse(_stream_with_own_session(), ...)
```

---

### 문제 2: pgvector 타입 오류

**증상:**
```
TypeError: object of type 'float' has no len()
```

**원인:**
`<=>` 연산자 결과에 `< 0.75` 비교를 하면 pgvector가 0.75를 벡터로 해석하려 함

**해결:**
`cast(..., Float)` 로 결과 타입을 명시

```python
# 오류 코드
.where(FileChunk.embedding.op("<=>")(query_embedding) < 0.75)

# 수정 코드
distance = cast(FileChunk.embedding.op("<=>")(query_embedding), Float)
.where(distance < 0.75)
```

---

### 문제 3: 히스토리 중복

**증상:**
LLM이 같은 질문을 두 번 받아서 어색한 답변 생성

**원인:**
```python
await save_user_message(...)    # 현재 질문 DB 저장
messages = await get_recent_messages(...)  # 방금 저장한 게 포함됨!
# → LLM에 현재 질문이 히스토리 + human turn 두 번 들어감
```

**해결:**
메시지 저장 순서 변경
```
이전: save_user → get_history → LLM → save_ai
이후: get_history → LLM → save_user → save_ai
```

---

### 문제 4: 임계값 튜닝

**증상:**
- 임계값 0.5 → 관련 있는 문서도 제외됨 ("참고할 문서가 없습니다")
- 임계값 1.0 → 관련 없는 문서도 포함

**해결 과정:**
로그로 실제 거리값 측정

```python
logger.info("RAG chunk: distance=%.4f, content_preview=%r", dist, chunk.content[:50])
```

측정 결과:
```
관련 있는 문서: 0.64 ~ 0.74
관련 없는 문서: 0.80 이상
```

→ 임계값 **0.75** 로 설정

---

## 9. 데이터 모델

```
files 테이블
├── id (UUID)
├── user_id  ← Keycloak JWT의 sub 클레임
├── filename
├── minio_path  ← {user_id}/{file_id}/{filename}
├── index_status  ← pending → indexing → indexed / failed / unsupported
└── deleted_at  ← 삭제 시 설정 (하드 삭제 전 RAG 격리용)

file_chunks 테이블
├── id (UUID)
├── file_id → files.id (CASCADE DELETE)
├── user_id
├── chunk_index  ← 몇 번째 청크인지
├── content (TEXT)  ← 원본 텍스트
├── embedding (Vector(1536))  ← pgvector
└── page_number  ← PDF 페이지 번호 or PPTX 슬라이드 번호
```

---

## 10. 용어 정리

| 용어 | 설명 |
|---|---|
| RAG | Retrieval-Augmented Generation. 검색 결과를 LLM에 전달해 답변 생성 |
| 청킹 | 텍스트를 일정 크기로 자르는 것 |
| 임베딩 | 텍스트를 숫자 벡터로 변환하는 것 |
| 벡터 | 숫자 배열. 여기서는 1536개 숫자로 텍스트 의미를 표현 |
| 코사인 거리 | 두 벡터의 방향 차이. 0에 가까울수록 유사 |
| pgvector | PostgreSQL 벡터 연산 확장. `<=>` 연산자로 유사도 검색 |
| LangChain | LLM 연동 도구 모음. 임베딩/LLM 호출/메시지 형식 처리 |
| SSE | Server-Sent Events. 서버 → 클라이언트 실시간 스트리밍 |
| AsyncGenerator | `yield` 로 값을 하나씩 비동기 반환하는 Python 함수 |
| 임계값 | 유사도 기준점. 초과하면 관련 없는 문서로 판단 |
