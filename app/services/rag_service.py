from __future__ import annotations

import json
import logging
import uuid as _uuid
from typing import AsyncGenerator

from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from app.core.config import settings
from app.services.chat_service import (
    get_recent_messages,
    get_session,
    save_assistant_message,
    save_user_message,
    set_session_title,
)
from app.services.file_service import get_file, search_similar_chunks

logger = logging.getLogger(__name__)


async def stream_rag_response(
    db,
    session_id,
    user_id: str,
    query: str,
) -> AsyncGenerator[str, None]:
    """Yield SSE events: token* → sources → done (or error)."""

    # 1. 세션 제목 설정 (첫 메시지일 때)
    session = await get_session(db, session_id, user_id)
    if session and not session.title:
        await set_session_title(db, session_id, query[:20])

    # 2. 히스토리 로드 (user 메시지 저장 전에 조회해야 중복 없음)
    messages = await get_recent_messages(db, session_id, limit=20)

    # 3. query embedding 생성
    api_key = SecretStr(settings.openai_api_key)
    embeddings_model = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=api_key,
    )

    # 검색 쿼리: 짧거나 맥락 의존 질문일 때만 직전 유저 질문을 앞에 붙임
    # LLM에 전달하는 히스토리와는 별개로 검색에만 사용
    _CONTINUATION_PATTERNS = ["더 말해", "계속", "이어서", "추가로"]
    _is_continuation = any(p in query for p in _CONTINUATION_PATTERNS)

    search_query = query
    if _is_continuation and messages:
        last_user_msg = next((m for m in reversed(messages) if m.role == "user"), None)
        if last_user_msg and last_user_msg.content.strip() != query.strip():
            search_query = f"{last_user_msg.content} {query}"
            logger.info("RAG search_query augmented: %r", search_query[:80])

    query_embedding = await embeddings_model.aembed_query(search_query)

    # 4. pgvector 코사인 거리 기반 유사도 검색 (deleted_at IS NULL 필터 포함)
    chunk_results = await search_similar_chunks(db, user_id, query_embedding, limit=5)
    for chunk, dist in chunk_results:
        logger.info("RAG chunk: file_id=%s, chunk_index=%d, distance=%.4f, content_preview=%r",
                    chunk.file_id, chunk.chunk_index, dist, chunk.content[:50])
    top_chunks = [chunk for chunk, _ in chunk_results]
    distances = {chunk.id: dist for chunk, dist in chunk_results}

    # 5. 색인 없음 처리
    if not top_chunks:
        fallback = "참고할 문서가 없습니다. 파일을 업로드하고 색인을 완료해 주세요."
        yield f"event: token\ndata: {json.dumps({'text': fallback}, ensure_ascii=False)}\n\n"
        yield f"event: sources\ndata: {json.dumps({'sources': []}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"
        await save_user_message(db, session_id, user_id, query)
        await save_assistant_message(db, session_id, user_id, fallback, [])
        return

    # 6. 컨텍스트 구성
    context = "\n\n".join(
        [f"[출처: {c.file_id}, 청크 {c.chunk_index}]\n{c.content}" for c in top_chunks]
    )

    # 7. 히스토리 → LangChain 메시지 변환 (현재 query 제외 — 히스토리는 과거 턴만)
    lc_messages = [SystemMessage(content=f"다음 문서를 참고하여 답변하세요:\n\n{context}")]
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            lc_messages.append(AIMessage(content=msg.content))
    lc_messages.append(HumanMessage(content=query))

    # 8. LLM 스트리밍
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=api_key,
        streaming=True,
    )

    full_answer = ""
    try:
        async for chunk_token in llm.astream(lc_messages):
            text = chunk_token.content
            if text:
                full_answer += text
                yield f"event: token\ndata: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"

        # 9. sources 이벤트 — 같은 파일은 가장 유사한 청크 1개만 표시
        file_name_cache: dict[str, str] = {}
        seen_files: set[str] = set()
        sources = []
        for c in top_chunks:  # top_chunks는 이미 distance 오름차순 정렬
            fid = str(c.file_id)
            if fid in seen_files:
                continue
            seen_files.add(fid)
            if fid not in file_name_cache:
                file_obj = await get_file(db, user_id, _uuid.UUID(fid))
                file_name_cache[fid] = file_obj.filename if file_obj else ""
            sources.append({
                "file_id": fid,
                "filename": file_name_cache[fid],
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
                "distance": round(distances.get(c.id, 0), 4),
            })
        yield f"event: sources\ndata: {json.dumps({'sources': sources}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

        # 10. 스트리밍 완료 후 DB 저장 (save_user → save_ai 순서)
        await save_user_message(db, session_id, user_id, query)
        await save_assistant_message(db, session_id, user_id, full_answer, sources)

    except Exception as exc:
        logger.error("LLM streaming error: %s", exc)
        yield "event: error\ndata: {\"message\": \"답변 생성 중 오류가 발생했습니다.\"}\n\n"
