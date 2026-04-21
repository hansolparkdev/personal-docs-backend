from __future__ import annotations

import io
import logging
import os
import tempfile

from pypdf import PdfReader

logger = logging.getLogger(__name__)


class UnsupportedFormatError(Exception):
    """Raised when a file format cannot be parsed by MarkItDown."""


def parse_to_pages(content: bytes, filename: str) -> list[tuple[int | None, str]]:
    """Parse file bytes into a list of (page_number, text) tuples.

    For PDF files, returns one tuple per page with 1-based page numbers.
    For non-PDF files, returns a single tuple with page_number=None using
    MarkItDown for parsing.

    Args:
        content: Raw file bytes.
        filename: Original filename (used to determine extension).

    Returns:
        List of (page_number, text) tuples. page_number is None for non-PDF.

    Raises:
        UnsupportedFormatError: If the file cannot be parsed or yields no text.
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
    else:
        markdown_text = parse_to_markdown(content, filename)
        return [(None, markdown_text)]


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
