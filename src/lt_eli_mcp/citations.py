"""Lithuanian TAR (data.gov.lt Spinta API) parsing + citation helpers.

The Lithuanian Register of Legal Acts (TAR) is published as open data through the data.gov.lt
Spinta API (dataset ``gov/lrsk/teises_aktai/Dokumentas``, CC BY 4.0). Each document carries the
full text in ``tekstas_lt`` and a canonical e-tar.lt URL in ``nuoroda``.

Lithuania has no data.europa.eu ELI for this dataset, so ``eli_uri`` carries the canonical
e-tar.lt legalAct URL (the stable national identifier). The connector flags this via ``eli_note``.

Citation contract:
- ``eli_uri``: the canonical e-tar.lt URL (``nuoroda``). NEVER invented - taken from the record.
- ``human_readable_citation``: the act title, with the official document number when present.
- ``source_url``: the same e-tar.lt page.
"""

from __future__ import annotations

import html as _html
import re
from typing import Any

PORTAL_BASE = "https://e-tar.lt"


def clean_text(text: str | None) -> str:
    """Normalise the full-text field (decode entities, collapse whitespace)."""
    if not text:
        return ""
    text = _html.unescape(text)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _s(row: dict[str, Any], key: str) -> str | None:
    v = row.get(key)
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def build_record(row: dict[str, Any]) -> dict[str, Any]:
    """Build a citation-bearing record from a Spinta document row (no full text)."""
    tar_kodas = _s(row, "tar_kodas")
    number = _s(row, "atv_dok_nr")
    title = _s(row, "pavadinimas")
    doc_type = _s(row, "rusis")
    nuoroda = _s(row, "nuoroda")
    date_adopted = _s(row, "priimtas")
    date_published = _s(row, "paskelbta_tar")
    validity = _s(row, "galioj_busena")

    if date_adopted:
        date_adopted = date_adopted[:10]
    if date_published:
        date_published = date_published[:10]

    eli = nuoroda  # canonical e-tar.lt URL; no data.europa.eu ELI exists for TAR
    human = f"{title} (Nr. {number})" if (title and number) else (title or number or tar_kodas)

    return {
        "tar_kodas": tar_kodas,
        "number": number,
        "document_type": doc_type,
        "title": title,
        "date_adopted": date_adopted,
        "date_published": date_published,
        "validity": validity,
        "eli_uri": eli,
        "human_readable_citation": human,
        "source_url": nuoroda,
    }
