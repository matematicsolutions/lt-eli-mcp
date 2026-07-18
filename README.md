# lt-eli-mcp

<!-- mcp-name: io.github.matematicsolutions/lt-eli-mcp -->

An MCP server for the Lithuanian **Register of Legal Acts (TAR)** via the **data.gov.lt** open-data
API. It searches Lithuanian legislation by title and fetches full text, with verifiable citations.

Part of the MateMatic `eu-legal-mcp` production line - after PL, DE, AT, ES, FI, IE, NL, SE, FR,
LU, DK, CZ and HR. Same citation contract, TAR source. This connector reads a REST-JSON open-data
API (the data.gov.lt Spinta endpoint).

> **Scope.** This MVP searches acts by title substring, returns metadata, and fetches the full
> Lithuanian text. ~CC BY 4.0 open data; acts are addressed by their TAR code (`tar_kodas`).
> Language: Lithuanian. Every response carries a `dataset_note`.
>
> **ELI is national, not data.europa.eu.** Lithuania has no `data.europa.eu` ELI for the TAR
> dataset. `eli_uri` carries the canonical `e-tar.lt` legalAct URL (the stable national
> identifier), which is also the `source_url`. Every response carries an `eli_note` saying so.

## The tools

| Tool | What it does |
|---|---|
| `lt_search` | Find acts whose title contains a substring (optionally by type). |
| `lt_get_act` | Metadata for an act by its TAR code. |
| `lt_get_text` | Full Lithuanian text of an act by its TAR code. |

Every response carries the contract: `eli_uri` (the `e-tar.lt` URL, e.g.
`https://e-tar.lt/portal/lt/legalAct/...`), `human_readable_citation` (title + official number),
and `source_url`.

## Install

Run it with no install step (once published to PyPI):

```bash
uvx lt-eli-mcp
```

Or from source:

```bash
cd lt-eli-mcp
pip install -e .
```

## Configure (Claude Code / any MCP client)

```json
{
  "mcpServers": {
    "lt-eli-mcp": { "command": "lt-eli-mcp" }
  }
}
```

### Windows 11 with Smart App Control

Smart App Control blocks unsigned executables, which covers `uvx.exe`, `pip.exe`
and the `lt-eli-mcp.exe` launcher that pip writes at install time. The `python.exe` and
`py.exe` from the python.org installer are signed by the Python Software
Foundation, so running the module through the interpreter works:

```bash
python -m pip install lt-eli-mcp
python -m lt_eli_mcp
```

`pip.exe` is blocked for the same reason, so install with `python -m pip`, not
`pip install`. If `python` is not on PATH, use the Windows launcher: `py -3 -m lt_eli_mcp`.

```json
{ "mcpServers": { "lt-eli-mcp": { "command": "python", "args": ["-m", "lt_eli_mcp"] } } }
```

Do not turn Smart App Control off to work around this - it cannot be re-enabled
without reinstalling Windows.

Environment:

- `LT_ELI_BASE_URL` - default `https://get.data.gov.lt`
- `LT_ELI_CACHE_DIR` - default `~/.matematic/cache/lt-eli`
- `LT_ELI_AUDIT_DIR` - default `~/.matematic/audit`

No API key. The data.gov.lt open-data API is keyless.

## Governance

- **Public data only** - read-only against data.gov.lt; no client data leaves the machine.
- **Audit log** - every tool call appends one JSON line to `~/.matematic/audit/lt-eli-mcp.jsonl`.
- **Vendor-neutral** - talks only to `get.data.gov.lt`; no LLM provider, no telemetry.
- **Verifiable citations** - every response is independently checkable via `source_url`.

See `CONSTITUTION.md` and `DISCOVERY.md`.

## Tests

```bash
pip install -e ".[dev]"
pytest tests/test_instructions_drift.py tests/test_parse.py -v   # offline
pytest tests/test_smoke.py -v                                    # hits live data.gov.lt
```

## Licence

Apache-2.0. © Matematic Solutions / Wieslaw Mazur. TAR data is CC BY 4.0; relayed with attribution
and a `source_url`.
