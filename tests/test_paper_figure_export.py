from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
import re
import shutil
import subprocess

import matplotlib.pyplot as plt
from PIL import Image
import pytest

import boec.paper_figures.export as export
from boec.paper_figures.core import FigureBundle
from boec.paper_figures.fonts import font_manifest
from boec.paper_figures.figure1 import build_figure1
from boec.paper_figures.export import build_all
from boec.paper_figures.layout import editorial_figure
from boec.paper_figures.style import get_preset


def test_build_all_writes_complete_bundle(tmp_path):
    manifest = build_all(Path("results"), tmp_path, "portable")
    figure_dir = tmp_path / "portable"
    for figure_id in ("fig1", "fig2", "fig3", "fig4", "fig5"):
        for suffix in (
            "pdf", "svg", "tiff", "png", "data.json", "alt.txt", "caption.txt", "description.txt"
        ):
            output = figure_dir / f"{figure_id}.{suffix}"
            assert output.exists() and output.stat().st_size > 100
    assert manifest["preset"]["width_mm"] == 178.0
    assert list(manifest["figures"]) == ["fig1", "fig2", "fig3", "fig4", "fig5"]
    assert manifest["font"]["family"] == "Charis SIL"
    assert manifest["font"]["path"].endswith("CharisSIL-Regular.ttf")
    assert len(manifest["font"]["sha256"]) == 64
    assert manifest["font"]["assets"] == font_manifest()
    assert set(manifest["supplementary_reservations"]) == {f"S{i}" for i in range(1, 12)}
    assert (tmp_path / "build-manifest.json").exists()
    assert (tmp_path / "paper-figures-contact-sheet.png").exists()
    assert (tmp_path / "paper-figures-grayscale-review.png").exists()
    assert (tmp_path / "paper-figures-deuteranopia-review.png").exists()


def test_raster_dimensions_match_declared_dpi(tmp_path):
    build_all(Path("results"), tmp_path, "portable")
    with Image.open(tmp_path / "portable" / "fig2.png") as png, Image.open(
        tmp_path / "portable" / "fig2.tiff"
    ) as tiff:
        assert abs(png.width - round(178.0 / 25.4 * 450)) <= 3
        assert abs(tiff.width - round(178.0 / 25.4 * 600)) <= 3
        assert png.mode == tiff.mode == "RGB"


def test_export_bundle_strips_svg_trailing_whitespace(tmp_path):
    bundle = build_figure1(get_preset("portable"))
    export.export_bundle(bundle, tmp_path, "portable")

    assert all(
        line == line.rstrip()
        for line in (tmp_path / "fig1.svg").read_text(encoding="utf-8").splitlines()
    )


def test_export_validates_packaged_font_resolution_before_writing(tmp_path, monkeypatch):
    bundle = build_figure1(get_preset("portable"))

    def reject_shadowed_font():
        raise RuntimeError("publication font resolved outside packaged assets")

    monkeypatch.setattr(export, "validate_publication_fonts", reject_shadowed_font)
    with pytest.raises(RuntimeError, match="resolved outside packaged assets"):
        export.export_bundle(bundle, tmp_path, "portable")
    assert not (tmp_path / "fig1.pdf").exists()


@pytest.mark.skipif(shutil.which("pdffonts") is None, reason="pdffonts is required")
def test_pdf_embeds_unicode_charis_and_stix_without_type3(tmp_path):
    preset = get_preset("plos")
    style_path = files("boec.paper_figures").joinpath("paper.mplstyle")
    with plt.style.context(str(style_path)):
        figure, content = editorial_figure(
            preset,
            90,
            "Publication typography smoke test",
            "Packaged fonts only",
            rows=1,
            cols=1,
        )
        axis = figure.add_subplot(content[0, 0])
        axis.set_xlabel(r"$x^2 + \sigma$")
        bundle = FigureBundle("font-smoke", figure, {"A": {}}, "alt", "caption", "description")
        export.export_bundle(bundle, tmp_path, preset)

    result = subprocess.run(
        ["pdffonts", str(tmp_path / "font-smoke.pdf")],
        check=True,
        capture_output=True,
        text=True,
    )
    known_poppler_warning = "Syntax Warning: Mismatch between font type and embedded font file"
    assert set(result.stderr.splitlines()) <= {known_poppler_warning}
    assert "Type 3" not in result.stdout
    assert re.search(r"CharisSIL.*yes\s+yes\s+yes", result.stdout)
    assert re.search(r"STIXMath-Regular.*yes\s+yes\s+yes", result.stdout)


def test_panel_data_alt_text_and_manifest_are_traceable(tmp_path):
    manifest = build_all(Path("results"), tmp_path, "portable")
    data = json.loads((tmp_path / "portable" / "fig4.data.json").read_text())
    assert set(data) == {"A", "B", "C", "D"}
    assert len((tmp_path / "portable" / "fig4.alt.txt").read_text().split()) >= 25
    assert "Figure 4" in (tmp_path / "portable" / "fig4.caption.txt").read_text()
    assert len((tmp_path / "portable" / "fig4.description.txt").read_text().split()) >= 60
    for source, digest in manifest["sources"].items():
        assert len(digest) == 64 and Path(source).exists()
    for files in manifest["figures"].values():
        for record in files.values():
            assert len(record["sha256"]) == 64


def test_rebuild_is_deterministic(tmp_path):
    first = build_all(Path("results"), tmp_path / "one", "portable")
    second = build_all(Path("results"), tmp_path / "two", "portable")
    assert first == second
    assert (tmp_path / "one" / "build-manifest.json").read_bytes() == (
        tmp_path / "two" / "build-manifest.json"
    ).read_bytes()
    for figure_id in ("fig1", "fig2", "fig3", "fig4", "fig5"):
        for suffix in (
            "pdf", "svg", "tiff", "png", "data.json", "alt.txt", "caption.txt", "description.txt"
        ):
            a = (tmp_path / "one" / "portable" / f"{figure_id}.{suffix}").read_bytes()
            b = (tmp_path / "two" / "portable" / f"{figure_id}.{suffix}").read_bytes()
            assert a == b


def test_builder_failure_closes_figures_and_invalidates_manifest(tmp_path, monkeypatch):
    manifest_path = tmp_path / "build-manifest.json"
    manifest_path.write_text('{"valid": true}\n')
    before = set(plt.get_fignums())

    def broken_builder(_preset):
        plt.figure()
        raise RuntimeError("synthetic builder failure")

    monkeypatch.setattr(export, "build_figure1", broken_builder)
    with pytest.raises(RuntimeError, match="synthetic builder failure"):
        build_all(Path("results"), tmp_path, "portable")
    assert set(plt.get_fignums()) == before
    assert not manifest_path.exists()
