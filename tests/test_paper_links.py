from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _checker():
    path = ROOT / "scripts" / "check_paper_links.py"
    spec = importlib.util.spec_from_file_location("check_paper_links", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publication_reading_path_has_no_broken_or_stale_links() -> None:
    assert _checker().validate() == []


def test_original_protocols_are_archived_and_single_active_protocol_exists() -> None:
    assert (ROOT / "paper" / "PROTOCOLS.md").is_file()
    assert not list((ROOT / "docs").glob("SPADE-*-SPEC.md"))
    assert (ROOT / "archive" / "superseded-spade" / "docs" / "SPADE-DOE-CERTIFICATE-SPEC.md").is_file()
