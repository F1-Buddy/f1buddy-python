import pymupdf

from ..errors import SourceError


def render_pages(pdf: bytes, max_pages: int = 20, dpi: int = 150) -> tuple[list[bytes], int]:
    """(PNG bytes for the first `max_pages` pages, total page count)."""
    try:
        with pymupdf.open(stream=pdf, filetype="pdf") as doc:
            pages = [doc[i].get_pixmap(dpi=dpi).tobytes("png") for i in range(min(len(doc), max_pages))]
            return pages, len(doc)
    except Exception as e:
        raise SourceError("FIA", f"could not render PDF: {e}") from e
