## 1. DB 모델 변경

- [ ] 1.1 `FileChunk` ORM 모델에 `page_number` 컬럼 추가
  - 수정 파일: `app/db/models/file_chunk.py`

## 2. Alembic 마이그레이션

- [ ] 2.1 마이그레이션 스크립트 자동 생성 후 검토
  - 수정 파일: `alembic/versions/<timestamp>_add_page_number_to_file_chunks.py`
  - 명령: `alembic revision --autogenerate -m "add_page_number_to_file_chunks"`

## 3. 파일 파서 변경

- [ ] 3.1 PDF 포맷 감지 및 pypdf 페이지별 추출 로직 구현
  - 반환 타입: `list[tuple[int | None, str]]` — PDF는 `(page_num, text)`, 비PDF는 `(None, full_text)`
  - 수정 파일: `app/utils/file_parser.py`

## 4. 파일 서비스 변경

- [ ] 4.1 청킹 루프에서 `page_number` 함께 저장
  - `file_parser`의 반환값 순회 시 `page_num`을 `FileChunk.page_number`에 할당
  - 수정 파일: `app/services/file_service.py`

## 5. RAG 서비스 변경

- [ ] 5.1 sources 딕셔너리에 `page_number` 필드 추가
  - 수정 파일: `app/services/rag_service.py`

## 6. 스키마 변경

- [ ] 6.1 sources 응답 스키마에 `page_number: int | None` 필드 추가
  - 수정 파일: `app/schemas/chat.py` (또는 sources 관련 스키마 파일)
