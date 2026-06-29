# DISCOVERY - lt-eli-mcp (Lithuania / TAR via data.gov.lt)

Date: 2026-06-29. Source selection driven by Legal Data Hunter coverage data
(`worldwidelaw/legal-sources`): Lithuania's `LT/LegalBase` source is a clean, keyless REST-JSON
open-data API, confirmed by live probes.

## Why Lithuania, why this way

The Lithuanian Register of Legal Acts (TAR) is exposed through the data.gov.lt **Spinta** API
(dataset `gov/lrsk/teises_aktai/Dokumentas`, CC BY 4.0). It returns JSON with the full act text in
`tekstas_lt` - a REST-JSON open-data API, no scraping and no PDF.

## Endpoint (keyless, CC BY 4.0)

- Base: `https://get.data.gov.lt/datasets/gov/lrsk/teises_aktai/Dokumentas`
- Query is the Spinta expression in the raw query string:
  - exact fetch: `?tar_kodas="2014-21296"`
  - title search: `?pavadinimas.contains("duomen")&limit(50)`
  - projection: `?select(tar_kodas,atv_dok_nr,...)` (used by search to skip the heavy text field)
- Returns `{"_data": [ ... ]}`. TLS verifies normally.

## Record shape (probed)

`tar_kodas` (the stable code, e.g. "2014-21296"), `atv_dok_nr` (official number, e.g. "A1-682",
"XII-1943"), `rusis` (type, with Lithuanian diacritics: "Įstatymas" = law, "Įsakymas" = order,
"Rezoliucija" = resolution), `pavadinimas` (title), `priimtas` (adoption date), `paskelbta_tar`
(publication date), `nuoroda` (canonical `https://e-tar.lt/portal/lt/legalAct/{id}` URL),
`galioj_busena` (validity: "galioja" = in force / "negalioja" = repealed), `tekstas_lt` (full text).

> **Note.** `rusis="Istatymas"` (no ogonek) returns 0 - the value is "Įstatymas" with diacritics.
> Pass the exact Lithuanian spelling to `doc_type`.

## Citation contract (Art. 4)

- `eli_uri` = the record's `nuoroda` (canonical e-tar.lt URL). No `data.europa.eu` ELI exists; the
  e-tar.lt URL is the stable national identifier (`eli_note`).
- `human_readable_citation` = title + official number, e.g. "... (Nr. A1-682)".
- `source_url` = the same e-tar.lt page.

## Tools (MVP)

- `lt_search(contains, doc_type?, limit)` - title-substring search (light projection, no body).
- `lt_get_act(tar_kodas)` - metadata by TAR code.
- `lt_get_text(tar_kodas)` - full text from `tekstas_lt`.

## Deficiencies flagged (per WM's "some connectors may be deficient" steer)

- **National ELI, not European** - no `data.europa.eu` ELI; `eli_uri` is the e-tar.lt URL.
- **Title-only search** - `lt_search` matches the title, not the body.

## Deferred

- **Case law** - LITEKO / Supreme / Constitutional Court (separate sources).
- **Cursor pagination** - the Spinta cursor endpoint had known 500 issues; the MVP uses `limit()`.
- **Body full-text search** - not exposed by the dataset query API in a simple form.

## Licence / re-use

TAR open data is CC BY 4.0 (Lithuanian State Register). Read-only relay with attribution +
`source_url`. No key, no ToS gate. Distribution as a public connector is in line with the keyless
tier.
