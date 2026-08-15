import os
from pathlib import Path

os.environ.setdefault(
    "HUGGINGFACE_HUB_CACHE",
    str(Path(__file__).resolve().parents[4] / "models" / "hub"),
)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("DOCLING_INFERENCE_COMPILE_TORCH_MODELS", "false")

import json
from docling.document_converter import DocumentConverter

_converter = None


def _get_converter() -> DocumentConverter:
    """Return a process-wide docling converter, initialized once.

    Initializing a converter downloads/checks the layout, table and OCR models
    against HuggingFace Hub; with ``HF_HUB_OFFLINE=1`` the check is skipped and
    the locally cached models are used. Reusing the converter avoids repeating
    that setup for every document.
    """
    global _converter
    if _converter is None:
        _converter = DocumentConverter()
    return _converter

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
    converter = _get_converter()
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
