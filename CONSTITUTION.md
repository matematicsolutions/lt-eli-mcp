# Constitution of lt-eli-mcp

Version: 0.1.0
Date: 2026-06-29
Licence: Apache-2.0

`lt-eli-mcp` is an MCP server for the Lithuanian Register of Legal Acts (TAR) via the data.gov.lt
open-data API. It searches acts by title and fetches full text with verifiable citations. Case law
is not in this MVP.

The 4 principles below are inherited from the `eu-legal-mcp` line Constitution (Article IV).

---

## Art. 1. Public data only

The data.gov.lt Spinta API is the official open-data channel for the TAR (CC BY 4.0, keyless). The
server is read-only (SELECT queries only) and sends nothing beyond the requested code / search term.

## Art. 2. Mandatory audit log

Every tool call MUST append one JSON line to `~/.matematic/audit/lt-eli-mcp.jsonl`
(ts / tool / input_hash SHA-256 / output_count_or_size / duration_ms / status). Inability to write =
the tool returns an error, it does not silently skip.

## Art. 3. Vendor neutrality

No tool hardcodes an LLM provider, assumes a model, or adds commercial telemetry. The server talks
only to `get.data.gov.lt` and the local filesystem. Authentication: none; own backoff + cache.

## Art. 4. ELI citations and a human-readable citation are mandatory

Every response MUST carry three fields:
- `eli_uri`: the canonical `e-tar.lt` legalAct URL (from the record). NEVER invented. Lithuania has
  no `data.europa.eu` ELI for the TAR dataset, so this is the stable national identifier - every
  response carries an `eli_note` stating this.
- `human_readable_citation`: the act title, with the official document number when present.
- `source_url`: the same `e-tar.lt` page.

---

## Open points

1. **National vs European ELI** - TAR has no `data.europa.eu` ELI; the `e-tar.lt` URL is the stable
   identifier. Flagged via `eli_note`.
2. **Title-only search** - `lt_search` matches the title (`pavadinimas`), not the body of the law.
3. **Pagination** - the MVP returns up to `limit` hits; cursor pagination over the Spinta API is
   deferred.
4. **Case law** - Lithuanian court decisions (LITEKO, Supreme/Constitutional) are a later feature.

## Ewolucja konstytucji

Changes to art. 1-4 follow SEMVER + an entry in `CHANGELOG.md` + a `pyproject.toml` bump.

First version: 2026-06-29. Author: Wieslaw Mazur / MateMatic.
