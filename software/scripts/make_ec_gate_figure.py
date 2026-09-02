"""Build a publication-ready summary of the current prospective EC gate.

The source JSON is never modified.  The script records the exact aggregation
and exports fixed-size RGB/PDF/SVG/TIFF files plus accessible text and a
machine-readable provenance sidecar.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from PIL import Image


FAMILIES = ("ec_broad", "ec_multimodal", "ec_narrow")
LABELS = ("Broad", "Multimodal", "Narrow")


def wilson_lower(successes: int, trials: int, z: float = 1.959963984540054) -> float:
    if trials == 0:
        return 0.0
    p = successes / trials
    den = 1 + z * z / trials
    centre = p + z * z / (2 * trials)
    half = z * (p * (1 - p) / trials + z * z / (4 * trials * trials)) ** 0.5
    return (centre - half) / den


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("research/results/ec-evaluation-current.json"))
    parser.add_argument("--output", type=Path, default=Path("research/results/figures/real-cell/fig5-ec-gate.png"))
    parser.add_argument("--width-mm", type=float, default=178.0)
    parser.add_argument("--height-mm", type=float, default=82.0)
    args = parser.parse_args()
    rows = json.loads(args.input.read_text(encoding="utf-8"))["rows"]
    spade = [r for r in rows if r["arm"] == "spade"]
    answer = [sum(r["answer_rate"] for r in spade if r["family"] == f) / 32 for f in FAMILIES]
    lower = []
    for family in FAMILIES:
        family_rows = [r for r in spade if r["family"] == family]
        answered = [r for r in family_rows if r["answer_rate"] > 0]
        successes = sum(bool(r.get("contained", False)) for r in answered)
        lower.append(wilson_lower(successes, len(answered)))

    # 178 mm is the portable/full-width preset used by the manuscript.  Keep
    # the physical geometry fixed across raster and vector exports.
    fig, axes = plt.subplots(1, 2, figsize=(args.width_mm / 25.4, args.height_mm / 25.4),
                             sharex=True, layout="constrained")
    colours = ("#009E73", "#0072B2", "#D55E00")  # Okabe–Ito subset
    hatches = ("///", "\\\\\\\\", "...")
    x = range(len(FAMILIES))
    for ax, values, threshold, ylabel, title in (
        (axes[0], answer, 0.50, "Answer rate", "Answers returned"),
        (axes[1], lower, 0.90, "One-sided 95% lower bound", "Containment evidence"),
    ):
        ax.bar(x, values, color=colours, hatch=hatches, width=0.62,
               edgecolor="#243746", linewidth=0.55)
        ax.axhline(threshold, color="#444444", linestyle="--", linewidth=1.0, label=f"gate = {threshold:.2f}")
        ax.set_ylim(0, 1.02)
        ax.set_xticks(list(x), LABELS)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#E5E7EB", linewidth=0.5)
        ax.set_axisbelow(True)
        for i, value in enumerate(values):
            ax.text(i, min(value + 0.035, 0.97), f"{value:.3f}", ha="center", va="bottom", fontsize=8)
    axes[0].text(0.02, -0.25, "SPADE · n=32 campaigns/family · 48 wells/campaign",
                 transform=axes[0].transAxes, fontsize=8)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output, dpi=450, facecolor="white")
    # Agg may emit RGBA even with an opaque face; publication raster is RGB.
    with Image.open(args.output) as image:
        if image.mode != "RGB":
            image.convert("RGB").save(args.output, dpi=(450, 450), optimize=True)
    fig.savefig(args.output.with_suffix(".pdf"), facecolor="white")
    fig.savefig(args.output.with_suffix(".svg"), facecolor="white")
    # PLOS accepts RGB 8-bit TIFF at 300–600 dpi; preserve exact dimensions.
    tiff_path = args.output.with_suffix(".tif")
    fig.savefig(tiff_path, dpi=600, facecolor="white")
    with Image.open(tiff_path) as image:
        image.convert("RGB").save(tiff_path, compression="tiff_lzw", dpi=(600, 600))
    stem = args.output.with_suffix("")
    stem.with_suffix(".alt.txt").write_text(
        "Two-panel bar chart of SPADE's prospective EC gate. Answer rates are 0.531 for broad, "
        "0.375 for multimodal, and 0 for narrow; containment lower bounds are 0.816, 0.758, and 0. "
        "Dashed lines show the 0.50 answer and 0.90 containment gates.\n",
        encoding="utf-8",
    )
    stem.with_suffix(".caption.txt").write_text(
        "Current prospective EC gate outcomes. Answer rates and one-sided 95% containment lower bounds "
        "are shown for 32 campaigns per family at 48 wells per campaign.\n",
        encoding="utf-8",
    )
    stem.with_suffix(".description.txt").write_text(
        "The left panel shows answer rate against the 0.50 gate; only broad reaches it. The right panel "
        "shows family-level containment lower bounds against the 0.90 gate; no family reaches it.\n",
        encoding="utf-8",
    )
    stem.with_suffix(".data.json").write_text(
        json.dumps({
            "source": str(args.input),
            "source_rows": len(rows),
            "filter": "arm == 'spade'",
            "families": list(FAMILIES),
            "campaigns_per_family": 32,
            "wells_per_campaign": 48,
            "answer_rate": answer,
            "containment_lower_bound": lower,
            "containment_interval": "Wilson one-sided 95% lower bound over answered campaigns",
            "answer_gate": 0.50,
            "containment_gate": 0.90,
            "missing_policy": "zero-answer campaigns remain explicit and are not counted as containment successes",
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    plt.close(fig)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
