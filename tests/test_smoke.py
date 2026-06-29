"""Smoke tests - require internet, hit the live Lithuanian data.gov.lt TAR API.

Run manually:

    pytest tests/test_smoke.py -v
"""

from __future__ import annotations

import pytest

from lt_eli_mcp.server import lt_get_act, lt_get_text, lt_search

TAR = "2014-21296"  # a stable TAR record (an order, A1-682, 2014)


@pytest.mark.asyncio
async def test_smoke_get_act() -> None:
    act = await lt_get_act(TAR)
    assert act.tar_kodas == TAR
    assert act.number == "A1-682"
    assert act.title
    assert act.eli_uri == "https://e-tar.lt/portal/lt/legalAct/ce0f95d090d111e4bb408baba2bdddf3"
    assert act.source_url and act.source_url.startswith("https://e-tar.lt/")
    assert act.human_readable_citation


@pytest.mark.asyncio
async def test_smoke_get_text() -> None:
    text = await lt_get_text(TAR)
    assert text.content and len(text.content) > 1000
    assert text.tar_kodas == TAR
    assert text.byte_size and text.byte_size > 1000


@pytest.mark.asyncio
async def test_smoke_search() -> None:
    res = await lt_search(contains="duomen", limit=5)
    assert res.total >= 1
    for h in res.items:
        assert h.tar_kodas
        assert h.eli_uri and h.eli_uri.startswith("https://e-tar.lt/")
        assert h.title and "duomen" in h.title.lower()
