from __future__ import annotations

import io
import logging
import os
import re
import tempfile

from pypdf import PdfReader

logger = logging.getLogger(__name__)

# MarkItDown이 PPTX 슬라이드 번호를 삽입하는 패턴
_SLIDE_NUMBER_RE = re.compile(r"<!--\s*Slide number:\s*(\d+)\s*-->")

# 페이지 단위로 파싱 가능한 확장자
_PAGE_AWARE_EXTENSIONS = {".pptx", ".ppt"}


class UnsupportedFormatError(Exception):
    """Raised when a file format cannot be parsed by MarkItDown."""


def parse_to_pages(content: bytes, filename: str) -> list[tuple[int | None, str]]:
    """Parse file bytes into a list of (page_number, text) tuples.

    - PDF: pypdf로 페이지 단위 파싱 → (page_num, text)
    - PPTX/PPT: MarkItDown 변환 후 슬라이드 번호 주석으로 분리 → (slide_num, text)
    - 나머지: MarkItDown으로 전체 텍스트 → (None, text)
    """
    suffix = os.path.splitext(filename)[-1].lower()

    if suffix == ".pdf":
        try:
            reader = PdfReader(io.BytesIO(content))
            pages: list[tuple[int | None, str]] = []
            for i, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append((i, text))
            if not pages:
                raise UnsupportedFormatError(f"No text extracted from PDF: {filename}")
            return pages
        except UnsupportedFormatError:
            raise
        except Exception as exc:
            raise UnsupportedFormatError(f"Failed to parse PDF {filename}: {exc}") from exc

    markdown_text = parse_to_markdown(content, filename)

    if suffix in _PAGE_AWARE_EXTENSIONS:
        pages = _split_by_slide_number(markdown_text)
        if pages:
            return pages

    return [(None, markdown_text)]


def _split_by_slide_number(markdown_text: str) -> list[tuple[int, str]]:
    """MarkItDown PPTX 출력에서 슬라이드 번호 주석을 기준으로 분리."""
    parts = _SLIDE_NUMBER_RE.split(markdown_text)
    # split 결과: [앞부분, 슬라이드번호, 내용, 슬라이드번호, 내용, ...]
    pages: list[tuple[int, str]] = []
    i = 1
    while i < len(parts) - 1:
        slide_num = int(parts[i])
        text = parts[i + 1].strip()
        if text:
            pages.append((slide_num, text))
        i += 2
    return pages


def parse_to_markdown(content: bytes, filename: str) -> str:
    """Parse file bytes to markdown text using MarkItDown.

    Args:
        content: Raw file bytes.
        filename: Original filename (used to determine extension).

    Returns:
        Markdown string of the parsed content.

    Raises:
        UnsupportedFormatError: If the file format is not supported or parsing fails.
    """
    try:
        from markitdown import MarkItDown  # type: ignore[attr-defined]
    except ImportError as exc:
        raise UnsupportedFormatError("markitdown package is not available") from exc

    suffix = os.path.splitext(filename)[-1] or ".bin"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        md = MarkItDown()
        result = md.convert(tmp_path)
        return result.text_content
    except UnsupportedFormatError:
        raise
    except Exception as exc:
        logger.warning("MarkItDown parse failed for %s: %s", filename, exc)
        raise UnsupportedFormatError(f"Failed to parse {filename}: {exc}") from exc
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
