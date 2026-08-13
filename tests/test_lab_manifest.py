"""The file index over data/lab: coverage, classification, and checksum integrity."""

from __future__ import annotations

from pathlib import Path

import pytest

from boec.lab.manifest import (
    OVERLAY_FILES,
    build_file_index,
    classify,
    load_manifest,
    load_roles,
    verify_checksums,
)

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "lab"

pytestmark = pytest.mark.skipif(not LAB.exists(), reason="data/lab not present")


@pytest.fixture(scope="module")
def index():
    return build_file_index(LAB, verify=True)


def test_every_file_on_disk_is_indexed(index):
    on_disk = {
        p.relative_to(LAB).as_posix()
        for p in LAB.rglob("*")
        if p.is_file() and p.name != ".DS_Store" and not p.relative_to(LAB).as_posix().startswith("derived/")
    }
    assert {f.path for f in index} == on_disk


def test_no_file_is_classified_unknown(index):
    unknown = [f.path for f in index if f.modality == "unknown"]
    assert unknown == [], unknown


def test_modality_counts_match_the_committed_drop(index):
    counts: dict[str, int] = {}
    for f in index:
        counts[f.modality] = counts.get(f.modality, 0) + 1
    # The "235 microscopy" figure in BO-PURPOSE.md is images PLUS .metadata sidecars.
    # Split here because only the 121 images carry pixels: 114 Leica JPEG + 7 EVOS JPG.
    assert counts["flow_events"] == 52
    assert counts["microscopy_image"] == 121
    assert counts["microscopy_sidecar"] == 114
    assert counts["microscopy_image"] + counts["microscopy_sidecar"] == 235
    assert counts["flow_sidecar"] == 10
    assert counts["protocol"] == 2
    assert counts["plate_reader"] == 1


def test_every_leica_jpeg_has_a_metadata_sidecar(index):
    jpegs = {f.path for f in index if f.modality == "microscopy_image" and "/leica/" in f.path}
    sidecars = {f.path.removesuffix(".metadata") for f in index if f.modality == "microscopy_sidecar"}
    orphans = jpegs - sidecars
    assert orphans == set(), f"Leica images with no .metadata: {sorted(orphans)[:5]}"


def test_committed_files_still_match_their_manifest_checksums(index):
    manifest = load_manifest(LAB / "MANIFEST.sha256")
    rep = verify_checksums(index, manifest)
    assert rep.mismatched == [], f"corrupted since commit: {rep.mismatched}"
    assert rep.missing_on_disk == [], f"in manifest but gone: {rep.missing_on_disk}"
    assert rep.ok == 300


def test_only_the_overlay_and_self_describing_files_are_unmanifested(index):
    """MANIFEST.sha256 cannot list itself, and README.md is the note that explains it.

    Everything else without a manifest entry would be a file that entered the tree
    outside the committed drop, which is exactly what this check is for.
    """
    manifest = load_manifest(LAB / "MANIFEST.sha256")
    rep = verify_checksums(index, manifest)
    expected = set(OVERLAY_FILES) | {"MANIFEST.sha256", "README.md"}
    unexpected = [p for p in rep.unmanifested if p.rsplit("/", 1)[-1] not in expected]
    assert unexpected == [], unexpected


def test_roles_cover_every_non_overlay_file(index):
    missing = [f.path for f in index if f.role is None and not f.is_overlay]
    assert missing == [], missing


@pytest.mark.parametrize(
    "path,expected",
    [
        ("flow/2026-08-06/Exp_20260806_cd31-cd140a/f5.fcs", "flow_events"),
        ("flow/2026-08-06/Exp_20260806_1/Exp_20260806_1.xit", "flow_sidecar"),
        ("flow/2026-07-28/Exp_20260728_1/ExpSummaryForAPI.xml", "flow_sidecar"),
        ("microscopy/leica/2026-08-04/Leica_2026-08-04 fib5.jpeg", "microscopy_image"),
        ("microscopy/leica/2026-08-04/Leica_2026-08-04 fib5.jpeg.metadata", "microscopy_sidecar"),
        ("plate-reader/2026-06-22_endpoint-abs-562.xlsx", "plate_reader"),
        ("protocols/IPSC分化EC-3.docx", "protocol"),
        ("MANIFEST.sha256", "index"),
        ("BO-PURPOSE.md", "index"),
    ],
)
def test_classification_rules(path, expected):
    assert classify(path) == expected


def test_manifest_parses_paths_containing_spaces():
    manifest = load_manifest(LAB / "MANIFEST.sha256")
    assert "flow/2026-08-06/Exp_20260806_1/well 1.fcs" in manifest
    digest, size = manifest["flow/2026-08-06/Exp_20260806_1/well 1.fcs"]
    assert len(digest) == 64 and size > 0


def test_roles_csv_and_index_agree_on_size():
    """Sizes must match for data files.

    ``index`` files (README.md and friends) are living documents that get edited after
    the roles CSV is generated, so drift there is expected and not a data problem.
    """
    roles = load_roles(LAB / "bo_file_roles.csv")
    idx = {f.path: f for f in build_file_index(LAB, verify=False)}
    for path, row in roles.items():
        assert path in idx, f"roles names a file that is not on disk: {path}"
        if idx[path].modality == "index":
            continue
        assert idx[path].bytes == int(row["bytes"]), path
