# 챗 API 사용법

## 전체 흐름 개요

```
1. 세션 생성   POST /api/v1/chats
                   |
                   v
2. 메시지 전송  POST /api/v1/chats/{session_id}/messages
                   |
                   v
3. SSE 수신    text/event-stream
               token → token → ... → sources → done
```

챗은 반드시 세션을 먼저 생성해야 합니다. 하나의 세션은 여러 개의 대화 메시지를 포함합니다.

---

## 세션 생성

```bash
curl -X POST http://localhost:8000/api/v1/chats \
  -H "Authorization: Bearer <access_token>"
```

응답 예시 (201 Created):
```json
{
  "id": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
  "title": null,
  "created_at": "2026-04-20T10:00:00Z",
  "updated_at": "2026-04-20T10:00:00Z"
}
```

`title`은 처음 메시지를 전송할 때 자동으로 설정됩니다.

---

## 세션 제목 자동 설정

메시지를 처음 전송할 때, 세션의 `title`이 `null`이면 질문 텍스트의 앞 20자를 제목으로 자동 설정합니다.

```python
# rag_service.py 내부 동작
if session and not session.title:
    await set_session_title(db, session_id, query[:20])
```

예를 들어 "이 계약서의 위약금 조항을 알려주세요"라고 질문하면 세션 제목이 "이 계약서의 위약금 조항을 알"로 설정됩니다.

---

## 메시지 전송 및 SSE 수신

```bash
curl -X POST http://localhost:8000/api/v1/chats/aaaabbbb-cccc-dddd-eeee-ffff00001111/messages \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"content": "업로드한 문서의 주요 내용을 요약해 주세요"}' \
  --no-buffer
```

SSE 응답 예시:
```
event: token
data: {"text": "업로드"}

event: token
data: {"text": "하신"}

event: token
data: {"text": " 문서의 주요 내용은 다음과 같습니다:\n\n"}

event: token
data: {"text": "1. ..."}

event: sources
data: {"sources": [{"file_id": "123e4567-...", "filename": "", "chunk_index": 0}, {"file_id": "123e4567-...", "filename": "", "chunk_index": 1}]}

event: done
data: {}
```

---

## 세션 목록 조회

로그인한 유저의 모든 세션을 최신순으로 반환합니다(최대 50개).

```bash
curl http://localhost:8000/api/v1/chats \
  -H "Authorization: Bearer <access_token>"
```

응답 예시 (200 OK):
```json
[
  {
    "id": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
    "title": "업로드한 문서의 주요 내",
    "created_at": "2026-04-20T10:00:00Z",
    "updated_at": "2026-04-20T10:05:00Z"
  }
]
```

---

## 세션 상세 조회 (메시지 포함)

```bash
curl http://localhost:8000/api/v1/chats/aaaabbbb-cccc-dddd-eeee-ffff00001111 \
  -H "Authorization: Bearer <access_token>"
```

응답 예시 (200 OK):
```json
{
  "id": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
  "title": "업로드한 문서의 주요 내",
  "created_at": "2026-04-20T10:00:00Z",
  "updated_at": "2026-04-20T10:05:00Z",
  "messages": [
    {
      "id": "msg-uuid-1",
      "session_id": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
      "role": "user",
      "content": "업로드한 문서의 주요 내용을 요약해 주세요",
      "sources": null,
      "created_at": "2026-04-20T10:05:00Z"
    },
    {
      "id": "msg-uuid-2",
      "session_id": "aaaabbbb-cccc-dddd-eeee-ffff00001111",
      "role": "assistant",
      "content": "업로드하신 문서의 주요 내용은 다음과 같습니다...",
      "sources": [
        {"file_id": "123e4567-...", "filename": "", "chunk_index": 0}
      ],
      "created_at": "2026-04-20T10:05:01Z"
    }
  ]
}
```

---

## 세션 삭제

세션을 삭제하면 연결된 모든 메시지도 CASCADE로 삭제됩니다.

```bash
curl -X DELETE http://localhost:8000/api/v1/chats/aaaabbbb-cccc-dddd-eeee-ffff00001111 \
  -H "Authorization: Bearer <access_token>"
```

응답: 204 No Content (본문 없음)

---

## SSE 클라이언트 Python 예시 코드

`httpx` 라이브러리를 사용한 SSE 수신 예시입니다.

```python
import httpx
import json

BASE_URL = "http://localhost:8000/api/v1"
ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."  # 로그인으로 발급받은 토큰

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def create_session() -> str:
    """새 챗 세션 생성, session_id 반환"""
    resp = httpx.post(f"{BASE_URL}/chats", headers=headers)
    resp.raise_for_status()
    return resp.json()["id"]


def send_message_sse(session_id: str, message: str) -> dict:
    """메시지 전송 후 SSE 스트림 수신, 최종 결과 반환"""
    full_text = ""
    sources = []

    with httpx.stream(
        "POST",
        f"{BASE_URL}/chats/{session_id}/messages",
        headers=headers,
        json={"content": message},
        timeout=60.0,
    ) as response:
        response.raise_for_status()

        buffer = ""
        for raw_bytes in response.iter_bytes():
            buffer += raw_bytes.decode("utf-8")
            while "\n\n" in buffer:
                event_block, buffer = buffer.split("\n\n", 1)
                lines = event_block.strip().splitlines()

                event_type = None
                event_data = None
                for line in lines:
                    if line.startswith("event: "):
                        event_type = line[len("event: "):]
                    elif line.startswith("data: "):
                        event_data = json.loads(line[len("data: "):])

                if event_type == "token" and event_data:
                    text = event_data.get("text", "")
                    full_text += text
                    print(text, end="", flush=True)  # 실시간 출력

                elif event_type == "sources" and event_data:
                    sources = event_data.get("sources", [])

                elif event_type == "done":
                    print()  # 줄바꿈
                    break

                elif event_type == "error" and event_data:
                    print(f"\n오류 발생: {event_data.get('message')}")
                    break

    return {"answer": full_text, "sources": sources}


if __name__ == "__main__":
    # 1. 세션 생성
    session_id = create_session()
    print(f"세션 생성: {session_id}")

    # 2. 메시지 전송 및 SSE 수신
    result = send_message_sse(session_id, "업로드한 문서의 주요 내용을 요약해 주세요")
    print(f"\n출처: {result['sources']}")
```

---

## oaicite 주의사항

- SSE 스트리밍 특성상 HTTP 연결이 완료(done 이벤트)될 때까지 열린 상태로 유지됩니다.
- `token` 이벤트를 순서대로 연결하면 완성된 답변 텍스트가 됩니다.
- `sources` 이벤트는 `done` 직전에 1회만 전송됩니다.
- 네트워크 프록시 또는 일부 클라이언트에서 버퍼링이 발생할 수 있으므로, `X-Accel-Buffering: no` 헤더가 응답에 포함됩니다.

---

## 오류 응답

| HTTP 상태 | 발생 조건 |
|---|---|
| 401 Unauthorized | 토큰 없음 또는 무효 |
| 404 Not Found | 세션이 존재하지 않거나 다른 유저의 세션 |
