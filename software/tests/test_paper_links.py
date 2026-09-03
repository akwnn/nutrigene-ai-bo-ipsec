from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _checker():
    path = ROOT / "software" / "scripts" / "check_paper_links.py"
    spec = importlib.util.spec_from_file_location("check_paper_links", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_publication_reading_path_has_no_broken_or_stale_links() -> None:
    assert _checker().validate() == []


def test_original_protocols_are_archived_and_single_active_protocol_exists() -> None:
    assert (ROOT / "publication" / "manuscript" / "PROTOCOLS.md").is_file()
    assert not list((ROOT / "docs").glob("SPADE-*-SPEC.md"))
    assert (ROOT / "archive" / "superseded-spade" / "docs" / "SPADE-DOE-CERTIFICATE-SPEC.md").is_file()


def test_unqualified_stale_document_reference_is_rejected() -> None:
    checker = _checker()
    text = "The active protocol is documented at docs/SPADE-LC-CONFIRMATORY-SPEC.md."
    match = checker.STALE_DOC.search(text)

    assert match is not None
    assert not checker.stale_doc_reference_is_allowed(text, match)


@pytest.mark.parametrize("context", ["archived", "superseded", "stale", "correction", "rejected"])
def test_stale_document_reference_with_correction_context_is_allowed(context: str) -> None:
    checker = _checker()
    text = f"The {context} reference docs/SPADE-LC-CONFIRMATORY-SPEC.md is retained for the audit."
    match = checker.STALE_DOC.search(text)

    assert match is not None
    assert checker.stale_doc_reference_is_allowed(text, match)
