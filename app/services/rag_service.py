from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

import numpy as np
from langchain.schema import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import SecretStr

from app.core.config import settings

logger = logging.getLogger(__name__)


def _cosine_sim(a: list, b: list) -> float:
    arr_a = np.array(a, dtype=float)
    arr_b = np.array(b, dtype=float)
    denom = np.linalg.norm(arr_a) * np.linalg.norm(arr_b) + 1e-10
    return float(np.dot(arr_a, arr_b) / denom)


async def stream_rag_response(
    db,
    session_id,
    user_id: str,
    query: str,
) -> AsyncGenerator[str, None]:
    """Yield SSE events: token* → sources → done (or error)."""
    from app.services.chat_service import (
        get_recent_messages,
        get_session,
        save_assistant_message,
        save_user_message,
        set_session_title,
    )
    from app.services.file_service import get_indexed_chunks, get_file
    import uuid as _uuid

    # 1. 세션 제목 설정 (첫 메시지일 때)
    session = await get_session(db, session_id, user_id)
    if session and not session.title:
        await set_session_title(db, session_id, query[:20])

    # 2. user 메시지 저장
    await save_user_message(db, session_id, user_id, query)

    # 3. 색인 청크 조회 (user_id 필터 포함 — get_indexed_chunks 내부에서 강제)
    chunks = await get_indexed_chunks(db, user_id)

    # 4. 색인 없음 처리
    if not chunks:
        fallback = "참고할 문서가 없습니다. 파일을 업로드하고 색인을 완료해 주세요."
        yield f"event: token\ndata: {json.dumps({'text': fallback}, ensure_ascii=False)}\n\n"
        yield f"event: sources\ndata: {json.dumps({'sources': []}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"
        await save_assistant_message(db, session_id, user_id, fallback, [])
        return

    # 5. 히스토리 로드
    messages = await get_recent_messages(db, session_id, limit=20)

    # 6. pgvector 유사도 검색 (K=5, user_id 필터는 get_indexed_chunks에서 이미 적용)
    api_key = SecretStr(settings.openai_api_key)
    embeddings_model = OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=api_key,
    )
    query_embedding = await embeddings_model.aembed_query(query)

    scored = []
    for chunk in chunks:
        if chunk.embedding is not None:
            sim = _cosine_sim(query_embedding, chunk.embedding)
            scored.append((sim, chunk))
    scored.sort(key=lambda x: x[0], reverse=True)
    top_chunks = [c for _, c in scored[:5]]

    # 7. 컨텍스트 구성
    context = "\n\n".join(
        [f"[출처: {c.file_id}, 청크 {c.chunk_index}]\n{c.content}" for c in top_chunks]
    )

    # 8. 히스토리 → LangChain 메시지 변환
    lc_messages = [SystemMessage(content=f"다음 문서를 참고하여 답변하세요:\n\n{context}")]
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            lc_messages.append(AIMessage(content=msg.content))
    lc_messages.append(HumanMessage(content=query))

    # 9. LLM 스트리밍
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

        # 10. sources 이벤트 — files 테이블에서 파일명 조회
        file_name_cache: dict[str, str] = {}
        for c in top_chunks:
            fid = str(c.file_id)
            if fid not in file_name_cache:
                file_obj = await get_file(db, user_id, _uuid.UUID(fid))
                file_name_cache[fid] = file_obj.filename if file_obj else ""

        sources = [
            {
                "file_id": str(c.file_id),
                "filename": file_name_cache.get(str(c.file_id), ""),
                "chunk_index": c.chunk_index,
                "page_number": c.page_number,
            }
            for c in top_chunks
        ]
        yield f"event: sources\ndata: {json.dumps({'sources': sources}, ensure_ascii=False)}\n\n"
        yield "event: done\ndata: {}\n\n"

        # 11. DB 저장
        await save_assistant_message(db, session_id, user_id, full_answer, sources)

    except Exception as exc:
        logger.error("LLM streaming error: %s", exc)
        yield "event: error\ndata: {\"message\": \"답변 생성 중 오류가 발생했습니다.\"}\n\n"
