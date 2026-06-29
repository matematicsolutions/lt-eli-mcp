"""Offline parse tests - build_record + clean_text against a committed Spinta row fixture."""

from __future__ import annotations

import json
from pathlib import Path

from lt_eli_mcp.citations import build_record, clean_text

FIX = Path(__file__).parent / "fixtures"


def _row() -> dict:
    data = json.loads((FIX / "act_2014_21296.json").read_text(encoding="utf-8"))
    rows = data.get("_data", [])
    return rows[0]


def test_build_record_core_fields():
    rec = build_record(_row())
    assert rec["tar_kodas"] == "2014-21296"
    assert rec["number"] == "A1-682"
    assert rec["document_type"]  # rusis present
    assert rec["title"]  # pavadinimas present
    assert rec["date_adopted"] == "2014-12-31"
    assert rec["eli_uri"] == "https://e-tar.lt/portal/lt/legalAct/ce0f95d090d111e4bb408baba2bdddf3"
    assert rec["source_url"] == rec["eli_uri"]


def test_build_record_citation_has_number():
    rec = build_record(_row())
    assert rec["human_readable_citation"]
    assert "(Nr. A1-682)" in rec["human_readable_citation"]


def test_clean_text_normalizes():
    assert clean_text("a&amp;b\r\n\n\n\nc   d") == "a&b\n\nc d"
    assert clean_text(None) == ""
    assert clean_text("") == ""


def test_full_text_present_in_fixture_row():
    row = _row()
    assert len(clean_text(row.get("tekstas_lt"))) > 1000
