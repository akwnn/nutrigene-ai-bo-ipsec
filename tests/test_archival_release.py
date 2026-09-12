"""A local archive must preserve approved evidence without leaking other files."""
import hashlib
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

import pytest


def module():
    path = Path(__file__).resolve().parents[1] / "scripts/prepare_archival_release.py"
    assert path.is_file(), "missing safe local archival packager"
    spec = importlib.util.spec_from_file_location("archival_release", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def fixture_source(tmp_path):
    root = tmp_path / "source"
    (root / "src/boec").mkdir(parents=True)
    (root / "src/boec/example.py").write_text("VALUE = 1\n")
    (root / "README.md").write_text("Local draft\n")
    return root


def test_zip_is_deterministic_and_extraction_hashes_match(tmp_path):
    pack = module()
    root = fixture_source(tmp_path)
    paths = ["README.md", "src/boec/example.py"]
    first, second = tmp_path / "first.zip", tmp_path / "second.zip"
    manifest = pack.write_archive(root, first, paths)
    pack.write_archive(root, second, list(reversed(paths)))
    assert first.read_bytes() == second.read_bytes()
    assert manifest["status"] == "LOCAL_DRAFT_NOT_FOR_PUBLIC_DEPOSIT"
    assert manifest["license"]["granted"] is False
    assert manifest["scientific_state"] == {"development": "NO_SELECTION", "lockbox": "FROZEN_UNOPENED"}
    with ZipFile(first) as archive:
        assert set(archive.namelist()) == set(paths) | {"archive-manifest.json"}
        assert str(root) not in archive.read("archive-manifest.json").decode()
    extracted = tmp_path / "extracted"
    pack.verify_and_extract(first, extracted)
    for path in paths:
        assert (extracted / path).read_bytes() == (root / path).read_bytes()
        assert manifest["files"][path]["sha256"] == hashlib.sha256((root / path).read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        pack.write_archive(root, first, paths)
    with pytest.raises(FileExistsError):
        pack.verify_and_extract(first, extracted)


@pytest.mark.parametrize("path", [
    "../escape.py", "/tmp/escape.py", "src/boec/../secret.py",
    ".git/config", ".venv/bin/python", "data/lab/raw/patient.csv",
    "data/external/paper.pdf", "src/boec/lab/manifest.py", "tests/test_lab_fcs.py",
    "src/boec/.env", "src/boec/key.pem", "src/boec/font.ttf",
    "results/spade-lockbox-outcomes.json", "manuscript/submission.zip",
    "src\\boec\\escape.py",
])
def test_private_runtime_and_unsafe_paths_are_rejected(tmp_path, path):
    pack = module()
    root = fixture_source(tmp_path)
    with pytest.raises(ValueError):
        pack.write_archive(root, tmp_path / "unsafe.zip", [path])
    assert not (tmp_path / "unsafe.zip").exists()


def test_symlink_and_symlink_parent_are_rejected(tmp_path):
    pack = module()
    root = fixture_source(tmp_path)
    target = tmp_path / "outside.py"
    target.write_text("secret")
    (root / "src/boec/link.py").symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        pack.write_archive(root, tmp_path / "link.zip", ["src/boec/link.py"])
    (root / "scripts").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        pack.write_archive(root, tmp_path / "parent.zip", ["scripts/outside.py"])


def test_discovery_excludes_private_fixtures_and_requires_evidence(tmp_path):
    pack = module()
    root = fixture_source(tmp_path)
    for path in ["src/boec/lab/fcs.py", "src/boec/__pycache__/x.pyc", "scripts/build_lab_dataset.py",
                 "tests/test_lab_fcs.py", "data/lab/raw/secret.csv", "results/unreviewed.json"]:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("private")
    with pytest.raises(FileNotFoundError):
        pack.select_files(root)
    for path in pack.REQUIRED_FILES:
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_text("fixture")
    selected = pack.select_files(root)
    assert "src/boec/example.py" in selected
    assert not any("/lab/" in path or "test_lab_" in path or "__pycache__" in path for path in selected)
    assert "results/unreviewed.json" not in selected


def test_extract_rejects_changed_member_and_traversal(tmp_path):
    pack = module()
    root = fixture_source(tmp_path)
    good = tmp_path / "good.zip"
    pack.write_archive(root, good, ["README.md"])
    with ZipFile(good) as archive:
        manifest = archive.read("archive-manifest.json")
    corrupt = tmp_path / "corrupt.zip"
    with ZipFile(corrupt, "w") as archive:
        archive.writestr("archive-manifest.json", manifest)
        archive.writestr("README.md", "changed")
    with pytest.raises(ValueError, match="hash"):
        pack.verify_and_extract(corrupt, tmp_path / "bad")
    assert not (tmp_path / "bad").exists()
    hostile = tmp_path / "hostile.zip"
    with ZipFile(hostile, "w") as archive:
        archive.writestr("archive-manifest.json", json.dumps({"files": {"../escape": {"sha256": ""}}}))
        archive.writestr("../escape", "secret")
    with pytest.raises(ValueError):
        pack.verify_and_extract(hostile, tmp_path / "escape")


def test_existing_machine_paths_are_reported_without_rewriting(tmp_path):
    pack = module()
    root = fixture_source(tmp_path)
    original = b"source = '/Users/example/private/project'\n"
    (root / "src/boec/example.py").write_bytes(original)
    output = tmp_path / "paths.zip"
    manifest = pack.write_archive(root, output, ["src/boec/example.py"])
    assert manifest["preexisting_local_path_files"] == ["src/boec/example.py"]
    assert "/Users/example" not in json.dumps(manifest)
    with ZipFile(output) as archive:
        assert archive.read("src/boec/example.py") == original


def test_historical_gate_inputs_are_mandatory_not_silently_omitted():
    pack = module()
    assert {f"results/{name}.json" for name in (
        "d20-rescore", "k6-designspace", "k6-designspace-spread",
        "k6b-conservative-spread", "k1-replay-gate", "versionb",
        "q42-families", "q59-hartmann-no-screen", "q52-budget-to-target",
        "e2-grid", "fix1-terminal-rule",
    )} <= set(pack.REQUIRED_FILES)


def test_approved_licenses_are_required_in_the_complete_archive():
    pack = module()
    assert {"LICENSE", "LICENSE-CONTENT.md"} <= set(pack.REQUIRED_FILES)


def test_approved_license_files_are_preserved_and_reported(tmp_path):
    pack = module()
    root = fixture_source(tmp_path)
    repo = Path(__file__).resolve().parents[1]
    names = ["LICENSE", "LICENSE-CONTENT.md"]
    for name in names:
        assert (repo / name).is_file(), f"missing approved license: {name}"
        (root / name).write_bytes((repo / name).read_bytes())
    manifest = pack.write_archive(root, tmp_path / "licensed.zip", names + ["README.md"])
    assert manifest["license"]["granted"] is True
    assert manifest["license"]["software"] == "MIT"
    assert manifest["license"]["research_materials"] == "CC-BY-4.0"
    assert manifest["license"]["copyright_holders"] == ["Alana Wai Han Kwan", "Joseph Yung"]
    assert manifest["license"]["decisions_required"] == []
    assert manifest["status"] == "LOCAL_DRAFT_NOT_FOR_PUBLIC_DEPOSIT"
    with ZipFile(tmp_path / "licensed.zip") as archive:
        for name in names:
            assert archive.read(name) == (repo / name).read_bytes()


def test_partial_or_changed_license_declarations_cannot_report_approval(tmp_path):
    pack = module()
    root = fixture_source(tmp_path)
    repo = Path(__file__).resolve().parents[1]
    for name in ("LICENSE", "LICENSE-CONTENT.md"):
        assert (repo / name).is_file(), f"missing approved license: {name}"
        (root / name).write_bytes((repo / name).read_bytes())
    with pytest.raises(ValueError, match="license"):
        pack.write_archive(root, tmp_path / "partial.zip", ["LICENSE"])
    (root / "LICENSE").write_text("Unapproved replacement")
    with pytest.raises(ValueError, match="license"):
        pack.write_archive(root, tmp_path / "changed.zip", ["LICENSE", "LICENSE-CONTENT.md"])
    assert not (tmp_path / "partial.zip").exists()
    assert not (tmp_path / "changed.zip").exists()
