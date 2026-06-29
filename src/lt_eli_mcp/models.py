"""Pydantic v2 models for the Lithuanian TAR (data.gov.lt) API + lt-eli-mcp."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

DATASET_NOTE = (
    "The Lithuanian Register of Legal Acts (TAR) is served as open data via the data.gov.lt "
    "Spinta API (dataset gov/lrsk/teises_aktai/Dokumentas, CC BY 4.0). Acts are addressed by their "
    "TAR code (tar_kodas, e.g. '2014-21296'); discover acts with lt_search (matches the title). "
    "Full text is in the tekstas_lt field. Language: Lithuanian."
)

ELI_NOTE = (
    "Lithuania has no data.europa.eu ELI for the TAR dataset. eli_uri carries the canonical "
    "e-tar.lt legalAct URL (the stable national identifier), which is also the source_url."
)


class _Tolerant(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class Act(_Tolerant):
    """A Lithuanian legal act (from the TAR Spinta API)."""

    tar_kodas: str | None = None
    number: str | None = None
    document_type: str | None = None
    title: str | None = None
    date_adopted: str | None = None
    date_published: str | None = None
    validity: str | None = None

    # Citation contract (Art. 4 CONSTITUTION).
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    eli_note: str = ELI_NOTE
    dataset_note: str = DATASET_NOTE


class LawText(_Tolerant):
    """Result of ``lt_get_text`` (full text from tekstas_lt)."""

    tar_kodas: str | None = None
    title: str | None = None
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None
    format: str = "text/plain"
    content: str | None = None
    byte_size: int | None = None
    eli_note: str = ELI_NOTE
    dataset_note: str = DATASET_NOTE


class SearchHit(_Tolerant):
    """A single act in a ``lt_search`` result."""

    tar_kodas: str | None = None
    number: str | None = None
    document_type: str | None = None
    title: str | None = None
    date_adopted: str | None = None
    validity: str | None = None
    eli_uri: str | None = None
    human_readable_citation: str | None = None
    source_url: str | None = None


class SearchResult(_Tolerant):
    """Result of ``lt_search``."""

    total: int
    items: list[SearchHit] = Field(default_factory=list)
    dataset_note: str = DATASET_NOTE
