## Context

현재 `file_parser.py`는 MarkItDown 단일 라이브러리로 모든 포맷을 전체 텍스트 문자열로 반환한다. `file_service.py`는 이 문자열을 LangChain `CharacterTextSplitter`로 청킹하여 `FileChunk` 레코드를 생성하는데, 청크가 어느 페이지에서 왔는지 정보를 유지하지 않는다. `rag_service.py`는 검색된 청크의 메타데이터에서 `file_id`, `filename`, `chunk_index`만 sources에 포함한다.

## Goals / Non-Goals

**Goals:**
- PDF 파일의 청킹 결과에 페이지 번호(1-based)를 보존한다
- `event: sources` 이벤트에 `page_number`(PDF는 정수, 비PDF는 null)를 포함한다
- 기존 비PDF 파싱 경로를 변경하지 않는다
- 마이그레이션으로 기존 청크 레코드와 스키마 호환성을 유지한다

**Non-Goals:**
- PDF 이외 포맷(DOCX, PPTX 등)의 페이지 번호 추출
- 청크가 두 페이지에 걸친 경우의 범위 표현 (`page_start`/`page_end`)
- 프론트엔드 UI 변경

## Decisions

### 1. PDF 파싱 라이브러리를 pypdf로 교체 (PDF 전용)

MarkItDown은 PDF를 전체 텍스트로 반환하여 페이지 경계 정보가 소실된다. pypdf는 페이지 객체 단위로 텍스트를 추출하므로 페이지 번호를 그대로 보존할 수 있다.

**이유**: pypdf가 이미 requirements에 포함되어 있어 추가 의존성 없음. 비PDF 포맷은 MarkItDown을 그대로 사용하여 변경 범위를 최소화한다.

### 2. `file_parser.py` 반환 타입을 `list[tuple[int | None, str]]`으로 통일

PDF는 `[(1, "p1 text"), (2, "p2 text"), ...]`, 비PDF는 `[(None, "full text")]`를 반환한다. `file_service.py`가 포맷을 구분하지 않고 동일한 루프로 처리할 수 있다.

**이유**: 분기 로직을 service 레이어가 아닌 parser 레이어에서 캡슐화하여 service 코드 변경을 최소화한다.

### 3. `page_number` 컬럼을 nullable Integer로 추가

PDF가 아닌 파일이나 마이그레이션 이전에 생성된 기존 청크 레코드는 `page_number = null`로 처리한다. nullable 선택으로 하위 호환성을 보장한다.

**이유**: NOT NULL로 설정하면 기존 데이터 마이그레이션 시 기본값 결정이 필요하고, 비PDF 파일의 의미 없는 기본값(0 또는 -1)이 sources에 노출된다.

### 4. 청크가 페이지 경계를 넘는 경우 시작 페이지 번호 사용

한 페이지의 텍스트를 여러 청크로 분리할 때 모든 청크는 해당 페이지 번호를 공유한다. 청크가 페이지 경계를 넘는 경우는 페이지별로 먼저 분리 후 청킹하는 전략으로 회피한다.

**이유**: 페이지 단위로 먼저 분리하면 청크가 자연스럽게 페이지 내에 머문다. 청크 경계가 페이지 경계와 항상 일치하지는 않으나, 출처 근사값으로 충분하다.

## Risks / Trade-offs

- [pypdf 텍스트 품질]: pypdf의 PDF 텍스트 추출 품질이 MarkItDown보다 낮을 수 있음 (레이아웃 복잡한 PDF) → 실제 PDF 샘플로 품질 검증 필요. 품질 이슈 발생 시 pypdf로 페이지 분리 후 MarkItDown에 페이지별 바이트를 전달하는 혼합 방식 검토
- [기존 청크 재색인]: 기존에 저장된 PDF 청크는 `page_number = null` 상태로 남음. 재색인하지 않으면 기존 파일의 sources에는 `page_number: null`이 반환됨 → 재색인은 별도 운영 태스크로 분리
- [청크 분할 위치 변경]: 페이지별 분리 후 청킹으로 청크 개수와 경계가 기존과 달라질 수 있음. 이미 색인된 파일은 영향 없고 신규 업로드 파일부터 적용
