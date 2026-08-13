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

def parse_pdf(path: Path) -> tuple[str, dict]:
    converter = DocumentConverter()
    result = converter.convert(path)
    doc = result.document
    markdown_text = doc.export_to_markdown()
    return markdown_text, {}

PARSERS = {
    "txt": parse_txt,
    "md": parse_markdown,
    "json": parse_json,
    "csv": parse_csv,
    "pdf": parse_pdf
}
