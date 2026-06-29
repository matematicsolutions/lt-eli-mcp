"""Async httpx client for the Lithuanian TAR open-data API (get.data.gov.lt) with cache.

The data.gov.lt Spinta API is keyless and returns JSON (``{"_data": [...]}``). Queries use the
Spinta expression syntax in the raw query string (e.g. ``?tar_kodas="2014-21296"`` or
``?pavadinimas.contains("X")&limit(50)``), so we build the query expression ourselves, percent-
encode it, and hand it to httpx verbatim. We keep our own backoff + cache.
"""

from __future__ import annotations

import json
import urllib.parse
from typing import Any

import anyio
import httpx

from .cache import HttpCache

DEFAULT_BASE_URL = "https://get.data.gov.lt"
DATASET_PATH = "/datasets/gov/lrsk/teises_aktai/Dokumentas"
DEFAULT_TIMEOUT = httpx.Timeout(90.0, connect=15.0)
USER_AGENT = "lt-eli-mcp/0.1.0 (+https://github.com/matematicsolutions/lt-eli-mcp)"

_RETRY_STATUS = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 3

# Keep Spinta structural characters intact; everything else (incl. '"' and non-ASCII) is encoded.
_SAFE = "()=&.,!*"


def _esc(value: str) -> str:
    """Escape a value for a Spinta string literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


class TarClient:
    """Async client. Use as ``async with TarClient() as c: ...``."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        cache: HttpCache | None = None,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._cache = cache or HttpCache()
        self._http = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )

    async def __aenter__(self) -> TarClient:
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()
        self._cache.close()

    async def _select(self, expr: str, *, category: str) -> list[dict[str, Any]]:
        cache_key = f"{self.base_url}{DATASET_PATH}?{category}:{expr}"
        cached = self._cache.get(cache_key)
        if cached is not None and isinstance(cached, str):
            return json.loads(cached).get("_data", [])
        query = urllib.parse.quote(expr, safe=_SAFE)
        url = httpx.URL(f"{self.base_url}{DATASET_PATH}").copy_with(query=query.encode("ascii"))
        last_exc: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = await self._http.get(url)
                resp.raise_for_status()
                self._cache.set(cache_key, resp.text, ttl=HttpCache.ttl_for(category))
                return json.loads(resp.text).get("_data", [])
            except httpx.HTTPStatusError as exc:
                last_exc = exc
                if exc.response.status_code not in _RETRY_STATUS or attempt == _MAX_ATTEMPTS - 1:
                    raise
            except (httpx.TransportError, httpx.TimeoutException) as exc:
                last_exc = exc
                if attempt == _MAX_ATTEMPTS - 1:
                    raise
            await anyio.sleep(0.5 * (2**attempt))
        assert last_exc is not None
        raise last_exc

    async def get_by_tar(self, tar_kodas: str) -> list[dict[str, Any]]:
        """Fetch the document(s) with the given TAR code (exact match)."""
        expr = f'tar_kodas="{_esc(tar_kodas)}"'
        return await self._select(expr, category="act")

    # Light projection for search hits - excludes the heavy tekstas_lt full-text field.
    _SEARCH_SELECT = (
        "select(tar_kodas,atv_dok_nr,rusis,pavadinimas,priimtas,paskelbta_tar,nuoroda,galioj_busena)"
    )

    async def search(
        self, contains: str, doc_type: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Search documents whose title contains a substring, optionally filtered by type."""
        parts = [self._SEARCH_SELECT, f'pavadinimas.contains("{_esc(contains)}")']
        if doc_type:
            parts.append(f'rusis="{_esc(doc_type)}"')
        parts.append(f"limit({int(limit)})")
        expr = "&".join(parts)
        return await self._select(expr, category="search")
