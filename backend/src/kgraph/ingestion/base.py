"""Abstract base class for data sources.

Every data source (arXiv, local files, IEEE, etc.) implements this interface.
The pipeline only interacts with ``RawDocument``s, so swapping the source
never touches the downstream code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from kgraph.graph.models import RawDocument


@dataclass(frozen=True)
class SourceCapabilities:
    """Declares what a data source can do.

    The pipeline uses this to decide which operations are available instead
    of hard-coding source-specific logic.
    """

    can_search: bool = True
    can_fetch_fulltext: bool = True
    can_download_pdf: bool = True
    has_references: bool = False
    reference_format: str = "none"  # "arxiv" | "doi" | "none"


class DataSource(ABC):
    """Contract every data source must fulfil.

    Subclasses implement ``fetch`` at minimum; ``fetch_fulltext`` and
    ``download_pdf`` have default implementations that fall back to
    ``fetch`` when the source doesn't support richer operations.
    """

    @property
    @abstractmethod
    def capabilities(self) -> SourceCapabilities:
        ...

    @abstractmethod
    def fetch(self) -> list[RawDocument]:
        ...

    def fetch_fulltext(self, download_dir: str | Path = "data/papers") -> list[RawDocument]:
        """Download PDFs, parse them and return full-text documents.

        Default: calls ``fetch()`` and returns whatever content the source
        provides (abstracts for arXiv, full text for local files).
        Override in sources that can download + parse PDFs.
        """
        return self.fetch()

    def download_pdf(self, doc: RawDocument, download_dir: str | Path = "data/papers") -> Path | None:
        """Download the PDF for a single document.

        Default: returns ``None`` (source doesn't support PDF downloads).
        Override in sources that provide PDF URLs.
        """
        return None
