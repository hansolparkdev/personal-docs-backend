from __future__ import annotations

import logging
import os
import tempfile

logger = logging.getLogger(__name__)


class UnsupportedFormatError(Exception):
    """Raised when a file format cannot be parsed by MarkItDown."""


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
