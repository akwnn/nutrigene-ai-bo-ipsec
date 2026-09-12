"""Deterministic, provenance-preserving exports for the paper figures."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageOps

from .core import FigureBundle, assert_no_prohibited_content, sha256_file
from .evidence import (
    build_figure2_data,
    build_figure3_data,
    build_figure4_data,
    source_paths,
)
from .figure1 import build_figure1
from .figure2 import build_figure2
from .figure3 import build_figure3
from .figure4 import build_figure4
from .qa import assert_label_clearance, assert_registered_geometry, resolved_publication_font
from .style import VenuePreset, get_preset


SUPPLEMENTARY_RESERVATIONS = {
    f"S{i}": description
    for i, description in enumerate(
        (
            "terminal-rule contrasts across dimensions and noise",
            "per-campaign search and identification distributions",
            "confirmation and replication sensitivities after refresh",
            "quadratic saddle and in-region recommendation diagnostics",
            "regret and arrival curves against wells and rounds",
            "point-map small multiples across families",
            "type-I and type-II map-error components",
            "Murphy decomposition and reliability diagrams",
            "certificate matrix, empty rates, and feasibility exclusions",
            "posterior-draw and Monte Carlo sensitivity",
            "classical-design and unscreened-comparator diagnostics",
        ),
        1,
    )
}


def _git_value(*args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], check=True, capture_output=True, text=True
        ).stdout.strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def _manifest_time() -> str | None:
    """Use commit time, rather than wall-clock time, so rebuilds compare bytewise."""
    return _git_value("show", "-s", "--format=%cI", "HEAD")


def _strip_svg_trailing_whitespace(path: Path) -> None:
    """Keep generated SVGs compatible with Git's whitespace check."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    path.write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n",
        encoding="utf-8",
    )


def export_bundle(bundle: FigureBundle, output_dir: Path, preset: VenuePreset | str) -> dict[str, Any]:
    """Write all publication formats and machine-readable panel sidecars."""
    if isinstance(preset, str):
        preset = get_preset(preset)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        assert_no_prohibited_content(bundle.panel_data)
        assert_no_prohibited_content(bundle.alt_text)
        paths = {
            suffix: output_dir / f"{bundle.figure_id}.{suffix}"
            for suffix in (
                "pdf",
                "svg",
                "png",
                "tiff",
                "data.json",
                "alt.txt",
                "caption.txt",
                "description.txt",
            )
        }
        # A builder may inherit a style's rounded figure width; restore the venue's
        # physical width before rasterisation so pixels are exactly reproducible.
        width_in = preset.width_mm / 25.4
        bundle.figure.set_size_inches(width_in, bundle.figure.get_figheight(), forward=True)
        assert_registered_geometry(bundle.figure)
        if preset.name == "plos":
            for dpi in (preset.png_dpi, preset.tiff_dpi):
                bundle.figure.set_dpi(dpi)
                assert_label_clearance(bundle.figure)
        # Keep backend settings explicit at export time, independent of caller rcParams.
        export_rc = {
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "svg.hashsalt": "boec-paper-figures-v1",
        }
        fixed_date = datetime(2000, 1, 1, tzinfo=timezone.utc)
        with mpl.rc_context(export_rc):
            bundle.figure.savefig(
                paths["pdf"], format="pdf",
                metadata={"Creator": "boec.paper_figures", "CreationDate": fixed_date},
            )
            bundle.figure.savefig(
                paths["svg"], format="svg",
                metadata={"Creator": "boec.paper_figures", "Date": "2000-01-01T00:00:00+00:00"},
            )
            _strip_svg_trailing_whitespace(paths["svg"])
            bundle.figure.savefig(paths["png"], format="png", dpi=preset.png_dpi)
            bundle.figure.savefig(
                paths["tiff"], format="tiff", dpi=preset.tiff_dpi,
                pil_kwargs={"compression": "tiff_lzw"},
            )
        # Matplotlib's Agg backend commonly emits RGBA even for opaque artwork;
        # publication raster derivatives are explicitly RGB.
        for suffix in ("png", "tiff"):
            with Image.open(paths[suffix]) as image:
                if image.mode != "RGB":
                    converted = image.convert("RGB")
                    if suffix == "tiff":
                        converted.save(paths[suffix], dpi=(preset.tiff_dpi, preset.tiff_dpi), compression="tiff_lzw")
                    else:
                        converted.save(paths[suffix], dpi=(preset.png_dpi, preset.png_dpi))
        paths["data.json"].write_text(
            json.dumps(bundle.panel_data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        paths["alt.txt"].write_text(bundle.alt_text.strip() + "\n", encoding="utf-8")
        paths["caption.txt"].write_text(bundle.caption.strip() + "\n", encoding="utf-8")
        paths["description.txt"].write_text(
            bundle.long_description.strip() + "\n", encoding="utf-8"
        )
        return {
            name: {"path": path.name, "sha256": sha256_file(path)}
            for name, path in paths.items()
        }
    finally:
        plt.close(bundle.figure)


def make_contact_sheet(
    png_paths: list[Path],
    path: Path,
    *,
    review_mode: str = "colour",
) -> None:
    """Create a compact preview without changing the source figure files."""
    if review_mode not in {"colour", "grayscale", "deuteranopia"}:
        raise ValueError(f"unknown review mode {review_mode!r}")
    cards = []
    for png_path in png_paths:
        with Image.open(png_path) as source:
            image = source.convert("RGB")
        if review_mode == "grayscale":
            image = ImageOps.grayscale(image).convert("RGB")
        elif review_mode == "deuteranopia":
            # Machado et al. severe-deuteranomaly matrix, used here only as a
            # deterministic reviewer preview; canonical exports remain untouched.
            image = image.convert(
                "RGB",
                (
                    0.367, 0.861, -0.228, 0,
                    0.280, 0.673, 0.047, 0,
                    -0.012, 0.043, 0.969, 0,
                ),
            )
        image.thumbnail((1600, 1200), Image.Resampling.LANCZOS)
        card = ImageOps.expand(image, border=(30, 80, 30, 30), fill="white")
        ImageDraw.Draw(card).text(
            (30, 25), f"{png_path.stem} · {review_mode}", fill="#202124"
        )
        cards.append(card)
    if not cards:
        raise ValueError("contact sheet requires at least one PNG")
    width = max(card.width for card in cards) * 2
    row_heights = [
        max(cards[i].height for i in range(start, min(start + 2, len(cards))))
        for start in range(0, len(cards), 2)
    ]
    sheet = Image.new("RGB", (width, sum(row_heights)), "#E5E7EB")
    y = 0
    for start, height in zip(range(0, len(cards), 2), row_heights, strict=True):
        for offset, card in enumerate(cards[start : start + 2]):
            sheet.paste(card, (offset * width // 2, y))
        y += height
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path, dpi=(150, 150))


def write_manifest(manifest: dict[str, Any], path: Path) -> None:
    """Write a stable, human-readable build manifest."""
    assert_no_prohibited_content(manifest)
    Path(path).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_all(results_dir: Path, output_dir: Path, preset_name: str = "portable") -> dict[str, Any]:
    """Build Figures 1–4 from authoritative results and return the manifest."""
    preset = get_preset(preset_name)
    results_dir, output_dir = Path(results_dir), Path(output_dir)
    figure_dir = output_dir / preset.name
    # Never leave a previous manifest claiming validity once an overwrite starts.
    manifest_path = output_dir / "build-manifest.json"
    if manifest_path.exists():
        manifest_path.unlink()
    evidence_paths = source_paths(results_dir)
    if missing := [path for path in evidence_paths if not path.exists()]:
        raise FileNotFoundError(f"required evidence source is missing: {missing[0]}")
    source_hashes = {str(path): sha256_file(path) for path in evidence_paths}
    data2 = build_figure2_data(results_dir)
    data3 = build_figure3_data(results_dir)
    data4 = build_figure4_data(results_dir)
    # Build, export, and close one figure at a time; this keeps failures from
    # leaking open GUI/backend figures into subsequent builds.
    figures = {}
    for builder, data in (
        (build_figure1, None), (build_figure2, data2),
        (build_figure3, data3), (build_figure4, data4),
    ):
        before = set(plt.get_fignums())
        try:
            bundle = builder(preset) if data is None else builder(data, preset)
            records = export_bundle(bundle, figure_dir, preset)
            figures[bundle.figure_id] = {
                key: {**record, "path": str(Path(preset.name) / record["path"])}
                for key, record in records.items()
            }
        finally:
            # Covers builders that fail after creating a Figure but before
            # returning a FigureBundle (export_bundle handles its own case).
            for number in set(plt.get_fignums()) - before:
                plt.close(number)
    png_paths = [figure_dir / f"fig{i}.png" for i in range(1, 5)]
    make_contact_sheet(png_paths, output_dir / "paper-figures-contact-sheet.png")
    make_contact_sheet(
        png_paths,
        output_dir / "paper-figures-grayscale-review.png",
        review_mode="grayscale",
    )
    make_contact_sheet(
        png_paths,
        output_dir / "paper-figures-deuteranopia-review.png",
        review_mode="deuteranopia",
    )
    sources = {str(path): digest for path, digest in source_hashes.items()}
    for path, digest in source_hashes.items():
        if sha256_file(Path(path)) != digest:
            raise RuntimeError(f"evidence source changed during build: {path}")
    font_path = resolved_publication_font()
    manifest = {
        "built_at_utc": _manifest_time(),
        "code_commit": _git_value("rev-parse", "HEAD"),
        "figure_code_sha256": {str(path.relative_to(Path(__file__).resolve().parents[3])): sha256_file(path)
                               for path in sorted(Path(__file__).parent.glob("*.py"))},
        "preset": preset.__dict__,
        "sources": sources,
        "font": {
            "family": "Arial",
            "path": str(font_path),
            "sha256": sha256_file(font_path),
        },
        "figures": figures,
        "supplementary_reservations": SUPPLEMENTARY_RESERVATIONS,
    }
    write_manifest(manifest, manifest_path)
    return manifest
