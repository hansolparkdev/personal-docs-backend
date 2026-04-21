## MODIFIED Requirements

### Requirement: 파일 업로드

인증된 사용자가 파일을 `POST /api/v1/files`로 전송하면 서버는 크기·포맷을 검증한 뒤 원본을 MinIO에 저장하고, 메타데이터를 DB에 기록하며, 백그라운드에서 텍스트 추출·임베딩 색인을 수행한다. PDF 파일은 pypdf로 페이지별 텍스트를 추출하여 청킹 시 `page_number`를 기록한다. 사용자에게는 저장 완료 즉시 응답이 반환된다.

#### Scenario 1: PDF 파일 업로드 — 페이지 번호 기록

- **Given** 유효한 Keycloak JWT를 소지한 사용자가 있다
- **When** PDF 파일을 `POST /api/v1/files`로 전송한다
- **Then** 서버는 201을 반환하고, 백그라운드에서 pypdf 페이지별 텍스트 추출이 진행된다
- **And** 각 청크 레코드의 `page_number`에 해당 페이지의 1-based 번호가 저장된다
- **And** 동일 페이지에서 생성된 복수 청크는 같은 `page_number`를 공유한다

#### Scenario 2: 비PDF 파일 업로드 — page_number null 저장

- **Given** 유효한 Keycloak JWT를 소지한 사용자가 있다
- **When** PDF가 아닌 지원 포맷(DOCX, PPTX, XLSX, MD, TXT) 파일을 업로드한다
- **Then** 백그라운드에서 MarkItDown으로 전체 텍스트가 추출된다
- **And** 생성된 모든 청크 레코드의 `page_number`는 null로 저장된다

#### Scenario 3: PDF 파싱 실패 (pypdf 오류)

- **Given** 유효한 JWT를 소지한 사용자가 암호화되거나 손상된 PDF를 업로드한다
- **When** 백그라운드 태스크에서 pypdf 텍스트 추출이 실패한다
- **Then** MinIO의 원본 파일은 유지된다
- **And** `files.index_status`가 "failed"로 갱신된다
