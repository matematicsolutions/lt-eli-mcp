"""FastMCP entry point - Lithuanian TAR (data.gov.lt) tools.

Run:

    python -m lt_eli_mcp.server

Configuration via env:

- ``LT_ELI_CACHE_DIR`` (default ``~/.matematic/cache/lt-eli``)
- ``LT_ELI_AUDIT_DIR`` (default ``~/.matematic/audit``)
- ``LT_ELI_BASE_URL`` (default ``https://get.data.gov.lt``)
"""

from __future__ import annotations

import os

import httpx
from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .audit import AuditLogger, hash_input, timer
from .citations import build_record, clean_text
from .client import DEFAULT_BASE_URL, TarClient
from .models import Act, LawText, SearchHit, SearchResult

INSTRUCTIONS = """\
This MCP server exposes the Lithuanian Register of Legal Acts (TAR) through the data.gov.lt open-data API. It searches acts by title and returns metadata and full text. Every response carries a stable `eli_uri`, a `human_readable_citation` and a `source_url` (the citation contract).

## Call order

1. `lt_search` - find acts whose title contains a substring (e.g. `contains="duomenu"`), optionally filtered by `doc_type` (the Lithuanian `rusis`, e.g. "Istatymas"). Returns hits with the TAR code (`tar_kodas`), title and `eli_uri`. This is the discovery step - use it to find the `tar_kodas`.
2. `lt_get_act` - metadata for an act by its `tar_kodas` (e.g. "2014-21296"): title, official number, type, dates, validity, `eli_uri`.
3. `lt_get_text` - the full Lithuanian text of an act by its `tar_kodas`.

## Hard constraints

- **ELI is national, not data.europa.eu** - Lithuania has no `data.europa.eu` ELI for the TAR dataset; `eli_uri` carries the canonical `e-tar.lt` legalAct URL (the stable national identifier). Relay the `eli_note`. Do not invent it - it comes from the record.
- **Search matches the title** - `lt_search` filters on the act title (`pavadinimas`), not the body of the law.
- **The TAR code is the key** - address acts by `tar_kodas` (e.g. "2014-21296"); it is the stable identifier returned by search.
- **Every response has `human_readable_citation` + `source_url`** - cite both to the user.
- **Audit log JSONL** - every tool call appends to `~/.matematic/audit/lt-eli-mcp.jsonl`.

## Error iteration

Tools return a structured error with a `[code]` prefix:
- `invalid_arg` - a parameter is missing or invalid (e.g. empty search term, limit out of range).
- `not_found` - no act exists for that `tar_kodas`.
- `upstream_error` - a data.gov.lt API error (HTTP, timeout, malformed JSON). Retry once before surfacing.

## Response style

- Cite as `human_readable_citation` with the e-tar.lt URL from `eli_uri`.
- NEVER invent a TAR code, a citation or a URL - take each from the tool output.
"""


class ToolError(Exception):
    """Structured error for lt-eli MCP tools - visible to the LLM with a [code] prefix."""

    VALID_CODES = frozenset({"invalid_arg", "not_found", "upstream_error"})

    def __init__(self, code: str, message: str):
        if code not in self.VALID_CODES:
            raise ValueError(f"Unknown ToolError code: {code}. Valid: {sorted(self.VALID_CODES)}")
        self.code = code
        super().__init__(f"[{code}] {message}")


READ_ONLY = ToolAnnotations(
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
    openWorldHint=True,
)

mcp: FastMCP = FastMCP(name="lt-eli-mcp", instructions=INSTRUCTIONS)


def _base_url() -> str:
    return os.environ.get("LT_ELI_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def _audit() -> AuditLogger:
    return AuditLogger()


def _map_upstream(exc: Exception) -> Exception:
    if isinstance(exc, (httpx.HTTPStatusError, httpx.TransportError, httpx.TimeoutException)):
        return ToolError("upstream_error", f"data.gov.lt API error: {type(exc).__name__}: {exc}")
    if isinstance(exc, (KeyError, ValueError)):
        return ToolError("upstream_error", f"Malformed data.gov.lt response: {type(exc).__name__}: {exc}")
    return exc


# ---------------------------------------------------------------------------
# lt_search
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def lt_search(contains: str, doc_type: str | None = None, limit: int = 50) -> SearchResult:
    """Search Lithuanian acts whose title contains a substring.

    Args:
        contains: substring matched against the act title (Lithuanian ``pavadinimas``).
        doc_type: optional Lithuanian act type (``rusis``), e.g. ``"Istatymas"`` (law),
            ``"Isakymas"`` (order). Match the exact Lithuanian spelling.
        limit: max hits (1..200, default 50).

    Returns:
        ``SearchResult`` with ``items: list[SearchHit]``, each carrying the citation contract.
    """
    audit = _audit()
    if not contains or not contains.strip():
        raise ToolError("invalid_arg", "contains must be a non-empty search term.")
    if not 1 <= limit <= 200:
        raise ToolError("invalid_arg", "limit must be between 1 and 200.")
    input_hash = hash_input({"contains": contains, "doc_type": doc_type, "limit": limit})

    with timer() as t:
        try:
            async with TarClient(base_url=_base_url()) as client:
                rows = await client.search(contains.strip(), doc_type=doc_type, limit=limit)
        except Exception as exc:
            audit.log(tool="lt_search", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    items = []
    for row in rows:
        rec = build_record(row)
        items.append(SearchHit(
            tar_kodas=rec["tar_kodas"], number=rec["number"], document_type=rec["document_type"],
            title=rec["title"], date_adopted=rec["date_adopted"], validity=rec["validity"],
            eli_uri=rec["eli_uri"], human_readable_citation=rec["human_readable_citation"],
            source_url=rec["source_url"],
        ))
    result = SearchResult(total=len(items), items=items)
    audit.log(tool="lt_search", input_hash=input_hash, output_count_or_size=len(items),
              duration_ms=t.duration_ms, status="ok")
    return result


# ---------------------------------------------------------------------------
# lt_get_act
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def lt_get_act(tar_kodas: str) -> Act:
    """Fetch Lithuanian act metadata by its TAR code.

    Args:
        tar_kodas: e.g. ``"2014-21296"`` (from ``lt_search``).

    Returns:
        ``Act`` with ``eli_uri``, ``human_readable_citation``, ``source_url``.
    """
    audit = _audit()
    if not tar_kodas or not tar_kodas.strip():
        raise ToolError("invalid_arg", "tar_kodas must be a non-empty TAR code.")
    tar_kodas = tar_kodas.strip()
    input_hash = hash_input({"tar_kodas": tar_kodas})

    with timer() as t:
        try:
            async with TarClient(base_url=_base_url()) as client:
                rows = await client.get_by_tar(tar_kodas)
        except Exception as exc:
            audit.log(tool="lt_get_act", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    if not rows:
        raise ToolError("not_found", f"No act with tar_kodas={tar_kodas!r} in TAR.")
    act = Act.model_validate(build_record(rows[0]))
    audit.log(tool="lt_get_act", input_hash=input_hash, output_count_or_size=1,
              duration_ms=t.duration_ms, status="ok")
    return act


# ---------------------------------------------------------------------------
# lt_get_text
# ---------------------------------------------------------------------------


@mcp.tool(annotations=READ_ONLY)
async def lt_get_text(tar_kodas: str) -> LawText:
    """Fetch the full Lithuanian text of an act by its TAR code.

    Args:
        tar_kodas: e.g. ``"2014-21296"``.

    Returns:
        ``LawText`` with the citation contract and ``content`` (plain text).
    """
    audit = _audit()
    if not tar_kodas or not tar_kodas.strip():
        raise ToolError("invalid_arg", "tar_kodas must be a non-empty TAR code.")
    tar_kodas = tar_kodas.strip()
    input_hash = hash_input({"tar_kodas": tar_kodas})

    with timer() as t:
        try:
            async with TarClient(base_url=_base_url()) as client:
                rows = await client.get_by_tar(tar_kodas)
        except Exception as exc:
            audit.log(tool="lt_get_text", input_hash=input_hash, output_count_or_size=0,
                      duration_ms=t.duration_ms if t.duration_ms else 0, status="error",
                      error=f"{type(exc).__name__}: {exc}")
            raise _map_upstream(exc) from exc

    if not rows:
        raise ToolError("not_found", f"No act with tar_kodas={tar_kodas!r} in TAR.")
    row = rows[0]
    rec = build_record(row)
    text = clean_text(row.get("tekstas_lt"))
    if not text:
        raise ToolError("not_found", f"Act {tar_kodas} has no full text in TAR.")
    result = LawText(
        tar_kodas=rec["tar_kodas"],
        title=rec["title"],
        eli_uri=rec["eli_uri"],
        human_readable_citation=rec["human_readable_citation"],
        source_url=rec["source_url"],
        content=text,
        byte_size=len(text.encode("utf-8")),
    )
    audit.log(tool="lt_get_text", input_hash=input_hash, output_count_or_size=result.byte_size or 0,
              duration_ms=t.duration_ms, status="ok")
    return result


def main() -> None:
    """Run the MCP server over stdio (default for Claude Code)."""
    mcp.run()


if __name__ == "__main__":
    main()
