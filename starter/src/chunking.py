"""Implement fixed-size and structure-aware chunking."""
import re
from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split text into overlapping windows and retain page metadata."""
    text = page.text
    step = size - overlap
    chunks: list[Chunk] = []
    start = 0
    idx = 0

    while start < len(text):
        end = min(start + size, len(text))
        chunk_text = text[start:end].strip()
        if len(chunk_text) > 30:
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}_p{page.page}_f{idx:03d}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=chunk_text,
                    metadata={
                        **page.metadata,
                        "strategy": "fixed_size",
                        "chunk_index": idx,
                        "char_length": len(chunk_text)
                    }
                )
            )
            idx += 1
        if end >= len(text):
            break
        start += step

    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group paragraphs, split oversized paragraphs and retain metadata."""
    text = page.text
    raw_paras = [p.strip() for p in text.split("\n\n") if p.strip()]

    merged: list[str] = []
    buf: list[str] = []
    curr_len = 0

    for p in raw_paras:
        if len(p) > max_size:
            if buf:
                merged.append("\n\n".join(buf))
                buf, curr_len = [], 0
            # Đoạn dài hơn max_size thì ngắt theo câu
            sentences = re.split(r"(?<=[.!?])\s+", p)
            s_buf, s_len = [], 0
            for s in sentences:
                if s_len + len(s) > max_size and s_buf:
                    merged.append(" ".join(s_buf))
                    s_buf, s_len = [s], len(s)
                else:
                    s_buf.append(s)
                    s_len += len(s) + 1
            if s_buf:
                merged.append(" ".join(s_buf))
        else:
            if curr_len + len(p) > max_size and buf:
                merged.append("\n\n".join(buf))
                buf, curr_len = [p], len(p)
            else:
                buf.append(p)
                curr_len += len(p) + 2

    if buf:
        merged.append("\n\n".join(buf))

    chunks: list[Chunk] = []
    for idx, c_text in enumerate(merged):
        clean_chunk = c_text.strip()
        if len(clean_chunk) > 30:
            chunks.append(
                Chunk(
                    chunk_id=f"{page.document_id}_p{page.page}_b{idx:03d}",
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=clean_chunk,
                    metadata={
                        **page.metadata,
                        "strategy": "by_paragraph",
                        "chunk_index": idx,
                        "char_length": len(clean_chunk)
                    }
                )
            )

    return chunks
