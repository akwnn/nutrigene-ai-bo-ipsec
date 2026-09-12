"""The local journal bundle must be current, explicit, and not claim approval."""
import hashlib
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest


def package_module():
    path = Path("scripts/prepare_submission_bundle.py")
    assert path.is_file(), "missing submission packaging command"
    spec = importlib.util.spec_from_file_location("submission_package", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_bundle_preserves_bytes_and_lists_unresolved_author_requirements(tmp_path):
    module = package_module()
    root = Path.cwd()
    output = tmp_path / "submission.zip"
    module.prepare_bundle(root, output)
    with ZipFile(output) as archive:
        manifest = json.loads(archive.read("submission-manifest.json"))
        assert manifest["status"] == "AUTHOR_REVIEW_REQUIRED"
        assert manifest["unresolved_manuscript_fields"]
        assert manifest["required_author_actions"]
        assert manifest["not_a_public_archive"] is True
        assert set(archive.namelist()) == {
            "manuscript.docx", "cover-letter.docx", "Fig1.tiff", "Fig2.tiff",
            "Fig3.tiff", "Fig4.tiff", "S1_Table.csv", "S2_Table.csv", "S3_Table.csv",
            "submission-manifest.json",
        }
        for filename, record in manifest["files"].items():
            data = archive.read(filename)
            assert hashlib.sha256(data).hexdigest() == record["sha256"]
            assert data == (root / record["source"]).read_bytes()
    with pytest.raises(FileExistsError):
        module.prepare_bundle(root, output)


def test_hash_verification_rejects_stale_bytes(tmp_path):
    module = package_module()
    path = tmp_path / "input.txt"
    path.write_bytes(b"old")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    module.require_hash(path, digest)
    path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="stale"):
        module.require_hash(path, digest)


@pytest.mark.parametrize("expected", [False, True])
def test_docx_validation_rejects_wrong_letter_mode(monkeypatch, expected):
    module = package_module()
    manifest = {
        "source_sha256": "unused", "builder_sha256": "unused",
        "output_sha256": "unused", "include_figures": False,
        "cover_letter": not expected, "image_sha256": {},
    }
    monkeypatch.setattr(module, "_read_json", lambda path: manifest)
    monkeypatch.setattr(module, "require_hash", lambda path, digest: None)
    with pytest.raises(ValueError, match="wrong letter mode"):
        module._validate_docx(Path.cwd(), "example", "example", False, expected)


def test_manuscript_first_figure_citations_are_followed_by_their_figures():
    paragraphs = Path("manuscript/SPADE-PLOS-ONE.md").read_text().split("\n\n")
    import re
    for number in range(1, 5):
        first = next(i for i, text in enumerate(paragraphs)
                     if re.search(rf"\bFig(?:ure)? {number}(?:[A-D])?\b", text))
        assert paragraphs[first + 1].startswith("![")
        assert paragraphs[first + 2].startswith(f"**Fig {number}.")
