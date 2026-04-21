## MODIFIED Requirements

### Requirement: 출처 메타데이터 제공

스트리밍 응답의 `event: sources` 이벤트에는 답변 생성에 사용된 청크의 파일 식별자, 파일명, 청크 위치, 페이지 번호가 포함된다.

SSE sources 이벤트 형식 (변경 후):
```
event: sources
data: {"sources": [{"file_id": "...", "filename": "...", "chunk_index": 0, "page_number": 3}]}
```

PDF가 아닌 파일의 청크는 `page_number`가 null이다:
```
event: sources
data: {"sources": [{"file_id": "...", "filename": "...", "chunk_index": 0, "page_number": null}]}
```

#### Scenario 1: PDF 출처 — page_number 포함

- **Given** pgvector 검색으로 PDF 파일의 청크 3개가 사용된 경우
- **When** 스트리밍 완료 시점의 sources 이벤트
- **Then** `sources` 배열에 3개 항목 포함
- **And** 각 항목에 `file_id`, `filename`, `chunk_index`, `page_number` 필드 포함
- **And** `page_number`는 해당 청크가 속한 PDF 페이지의 1-based 정수

#### Scenario 2: 비PDF 출처 — page_number null

- **Given** pgvector 검색으로 PDF가 아닌 파일(예: DOCX, TXT)의 청크가 사용된 경우
- **When** 스트리밍 완료 시점의 sources 이벤트
- **Then** 각 항목의 `page_number` 값이 null

#### Scenario 3: 혼합 출처 (PDF + 비PDF)

- **Given** pgvector 검색으로 PDF 청크 2개와 TXT 청크 1개가 사용된 경우
- **When** 스트리밍 완료 시점의 sources 이벤트
- **Then** `sources` 배열에 3개 항목 포함
- **And** PDF 청크 항목의 `page_number`는 정수, TXT 청크 항목의 `page_number`는 null

#### Scenario 4: 색인 청크 없어 출처가 비어있는 경우

- **Given** 색인 완료 파일 없음으로 fallback 응답 처리된 경우
- **When** sources 이벤트 전송
- **Then** `sources` 배열이 빈 배열 `[]`
