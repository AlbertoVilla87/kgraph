import logging
from pathlib import Path

import pypdfium2 as pdfium
from tqdm import tqdm

from kgraph.ingestion.base import DataSource
from kgraph.graph.models import RawDocument
from kgraph.ingestion.parsers.parsers import PARSERS, parse_pdf_document

logging.basicConfig(level=logging.INFO)


def _count_pdf_pages(path: Path) -> int:
    """Return the number of pages in a PDF (fast, no full text extraction)."""
    pdf = pdfium.PdfDocument(str(path))
    try:
        return len(pdf)
    finally:
        pdf.close()


class LocalFileSource(DataSource):
    def __init__(self, folder: str, file_type: str, max_pages: int | None = None):
        self.folder = Path(folder)
        self.file_type = file_type
        self.max_pages = max_pages

        if file_type not in PARSERS:
            raise ValueError(f"Unsupported file_type: {file_type}. Available: {list(PARSERS.keys())}")

        self.parser = PARSERS[file_type]

    def fetch(self) -> list[RawDocument]:
        docs = []
        paths = sorted(self.folder.glob(f"*.{self.file_type}"))
        for path in tqdm(paths, desc="parsing documents", unit="doc"):
            if self.max_pages and self.file_type == "pdf":
                pages = _count_pdf_pages(path)
                if pages > self.max_pages:
                    logging.warning(
                        f"Skipping {path.name}: {pages} pages exceeds "
                        f"max_pages={self.max_pages}"
                    )
                    continue
            docling_doc = None
            if self.file_type in ("pdf", "md"):
                docling_doc = parse_pdf_document(path)
            if self.file_type == "pdf":
                text = docling_doc.export_to_markdown()
                metadata = {}
            else:
                text, metadata = self.parser(path)
            docs.append(RawDocument(
                id=path.stem,
                content=text,
                source=f"local_{self.file_type}",
                metadata=metadata,
                docling_doc=docling_doc,
            ))
        return docs