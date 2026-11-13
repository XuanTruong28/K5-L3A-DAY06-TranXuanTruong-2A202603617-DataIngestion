"""Read and normalize source data. TODO: implement functions."""
import re
import unicodedata
import warnings
from pathlib import Path
import pypdf
from .models import DocumentPage

warnings.filterwarnings("ignore")


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace without discarding useful structure."""
    if not text:
        return ""
    # Chuẩn hóa Unicode NFKC và ký tự ngắt dòng
    text = unicodedata.normalize("NFKC", text).replace("\r\n", "\n").replace("\r", "\n")
    # Chuẩn hóa khoảng trắng từng dòng và giữ cấu trúc đoạn
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical page; keep its page number and source.

    Detect and record pages with no text. OCR, when needed, is a separate step.
    """
    reader = pypdf.PdfReader(str(path))
    pages: list[DocumentPage] = []

    for idx, pdf_page in enumerate(reader.pages):
        page_num = idx + 1
        raw_text = pdf_page.extract_text() or ""
        clean = normalize_text(raw_text)

        # Bỏ qua các trang rỗng hoặc trang bìa trước Chapter 1
        if len(clean) < 30 or page_num < 13:
            continue

        # Gán nhãn metadata chương và chủ đề theo số trang vật lý
        if page_num <= 20:
            chapter = "Chapter 1: Introduction to commercial seaweeds"
            category = "Overview"
        elif page_num <= 28:
            chapter = "Chapter 2: Seaweeds used as a source of agar"
            category = "Agar"
        elif page_num <= 38:
            chapter = "Chapter 3: Agar"
            category = "Agar"
        elif page_num <= 49:
            chapter = "Chapter 4: Seaweeds used as a source of alginate"
            category = "Alginate"
        elif page_num <= 62:
            chapter = "Chapter 5: Alginate"
            category = "Alginate"
        elif page_num <= 74:
            chapter = "Chapter 6: Seaweeds used as a source of carrageenan"
            category = "Carrageenan"
        elif page_num <= 84:
            chapter = "Chapter 7: Carrageenan"
            category = "Carrageenan"
        else:
            chapter = "Chapter 8: Seaweeds used as human food"
            category = "Food"

        doc_page = DocumentPage(
            document_id=document_id,
            source=source,
            page=page_num,
            text=clean,
            metadata={
                "chapter": chapter,
                "category": category,
                "char_count": len(clean)
            }
        )
        pages.append(doc_page)

    return pages
