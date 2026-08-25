from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from boec.paper_figures.export import build_all


def test_build_all_writes_complete_bundle(tmp_path):
    manifest = build_all(Path("results"), tmp_path, "portable")
    figure_dir = tmp_path / "portable"
    for figure_id in ("fig1", "fig2", "fig3", "fig4"):
        for suffix in ("pdf", "svg", "tiff", "png", "data.json", "alt.txt"):
            output = figure_dir / f"{figure_id}.{suffix}"
            assert output.exists() and output.stat().st_size > 100
    assert manifest["preset"]["width_mm"] == 178.0
    assert set(manifest["figures"]) == {"fig1", "fig2", "fig3", "fig4"}
    assert set(manifest["supplementary_reservations"]) == {f"S{i}" for i in range(1, 12)}
    assert (tmp_path / "build-manifest.json").exists()
    assert (tmp_path / "paper-figures-contact-sheet.png").exists()


def test_raster_dimensions_match_declared_dpi(tmp_path):
    build_all(Path("results"), tmp_path, "portable")
    with Image.open(tmp_path / "portable" / "fig2.png") as png, Image.open(
        tmp_path / "portable" / "fig2.tiff"
    ) as tiff:
        assert abs(png.width - round(178.0 / 25.4 * 450)) <= 3
        assert abs(tiff.width - round(178.0 / 25.4 * 600)) <= 3
        assert png.mode == tiff.mode == "RGB"


def test_panel_data_alt_text_and_manifest_are_traceable(tmp_path):
    manifest = build_all(Path("results"), tmp_path, "portable")
    data = json.loads((tmp_path / "portable" / "fig3.data.json").read_text())
    assert set(data) == {"A", "B", "C", "D"}
    assert len((tmp_path / "portable" / "fig3.alt.txt").read_text().split()) >= 25
    for source, digest in manifest["sources"].items():
        assert len(digest) == 64 and Path(source).exists()
    for files in manifest["figures"].values():
        for record in files.values():
            assert len(record["sha256"]) == 64


def test_rebuild_is_deterministic(tmp_path):
    first = build_all(Path("results"), tmp_path / "one", "portable")
    second = build_all(Path("results"), tmp_path / "two", "portable")
    # Output paths are intentionally absolute for a directly consumable manifest;
    # compare the content and hashes, not each temporary directory name.
    for manifest in (first, second):
        for records in manifest["figures"].values():
            for record in records.values():
                record["path"] = Path(record["path"]).name
    assert first == second
    for figure_id in ("fig1", "fig2", "fig3", "fig4"):
        for suffix in ("pdf", "svg", "tiff", "png", "data.json", "alt.txt"):
            a = (tmp_path / "one" / "portable" / f"{figure_id}.{suffix}").read_bytes()
            b = (tmp_path / "two" / "portable" / f"{figure_id}.{suffix}").read_bytes()
            assert a == b
