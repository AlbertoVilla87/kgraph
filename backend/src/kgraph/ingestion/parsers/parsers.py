import os

os.environ.setdefault("DOCLING_INFERENCE_COMPILE_TORCH_MODELS", "false")

import json
from pathlib import Path
from docling.document_converter import DocumentConverter

def parse_txt(path: Path) -> tuple[str, dict]:
    return path.read_text(), {}

def parse_markdown(path: Path) -> tuple[str, dict]:
    return parse_txt(path)

def parse_json(path: Path) -> tuple[str, dict]:
    data = json.loads(path.read_text())
    text = data.get("text", "")
    metadata = {k: v for k, v in data.items() if k != "text"}
    return text, metadata

def parse_csv(path: Path) -> tuple[str, dict]:
    raise NotImplementedError("CSV parsing not implemented yet")

def parse_pdf_document(path: Path):
    """Convert a PDF into a docling ``DoclingDocument``.

    Keeping the structured document (instead of only its markdown export)
    enables section-aware segmentation via docling's ``HierarchicalChunker``,
    which the plain-text pipeline discards.
    """
    converter = DocumentConverter()
    result = converter.convert(path)
    return result.document

def parse_pdf_full(path: Path) -> tuple[object, str]:
    """Convert a PDF and return ``(docling_document, markdown_text)``."""
    doc = parse_pdf_document(path)
    return doc, doc.export_to_markdown()

def parse_pdf(path: Path) -> tuple[str, dict]:
    _, markdown_text = parse_pdf_full(path)
    return markdown_text, {}

PARSERS = {
    "txt": parse_txt,
    "md": parse_markdown,
    "json": parse_json,
    "csv": parse_csv,
    "pdf": parse_pdf
}
