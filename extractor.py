import os
import pdfplumber
import pytesseract

from PIL import Image
from docx import Document
from pdf2image import convert_from_path


def extract_text_from_pdf(file_path: str) -> str:
    text = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)

    # fallback OCR
    if len(" ".join(text).strip()) < 50:
        images = convert_from_path(file_path, dpi=300)
        for img in images:
            text.append(pytesseract.image_to_string(img))

    return "\n".join(text)


def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    text = []

    for para in doc.paragraphs:
        if para.text.strip():
            text.append(para.text.strip())

    return "\n".join(text)


def extract_text_from_image(file_path: str) -> str:
    return pytesseract.image_to_string(Image.open(file_path))


def extract_resume_text(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext == ".docx":
        return extract_text_from_docx(file_path)
    elif ext in [".png", ".jpg", ".jpeg"]:
        return extract_text_from_image(file_path)
    else:
        raise ValueError("Unsupported file type")