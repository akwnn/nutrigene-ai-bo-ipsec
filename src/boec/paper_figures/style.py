from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class MethodStyle:
    label: str
    colour: str
    marker: str
    fill: str = "full"


@dataclass(frozen=True)
class VenuePreset:
    name: str
    width_mm: float
    body_pt: float
    panel_pt: float
    png_dpi: int = 450
    tiff_dpi: int = 600

    def figsize(self, height_mm: float) -> tuple[float, float]:
        return self.width_mm / 25.4, height_mm / 25.4


METHOD_STYLES = {
    "spade_cf_m0": MethodStyle("SPADE", "#009E73", "o"),
    "versionb": MethodStyle("SPADE", "#009E73", "o"),
    "qlogei": MethodStyle("qLogEI", "#0072B2", "^", "none"),
    "qlognei": MethodStyle("qLogNEI", "#0072B2", "^"),
    "doe": MethodStyle("Classical DoE", "#D55E00", "s"),
    "lhs": MethodStyle("Latin hypercube", "#6B7280", "D", "none"),
    "sobol": MethodStyle("Sobol", "#6B7280", "D"),
    "random": MethodStyle("Random", "#6B7280", "P", "none"),
}

PRESETS = {
    "portable": VenuePreset("portable", 178.0, 7.5, 8.0),
    "rsc": VenuePreset("rsc", 171.0, 7.5, 8.0),
    "nature": VenuePreset("nature", 183.0, 7.0, 8.0),
    "plos": VenuePreset("plos", 178.0, 9.0, 10.0),
}

PresetArg: TypeAlias = VenuePreset | str | None


def get_preset(name: str) -> VenuePreset:
    try:
        return PRESETS[name]
    except KeyError as exc:
        raise ValueError(f"unknown venue preset {name!r}; choose {sorted(PRESETS)}") from exc


def method_style(arm: str) -> MethodStyle:
    if arm.startswith("spade_cf_"):
        return METHOD_STYLES["spade_cf_m0"]
    try:
        return METHOD_STYLES[arm]
    except KeyError as exc:
        raise ValueError(f"no visual encoding registered for arm {arm!r}") from exc


def _resolve_preset(preset: PresetArg) -> VenuePreset:
    if preset is None:
        return PRESETS["portable"]
    if isinstance(preset, VenuePreset):
        return preset
    return get_preset(preset)


def apply_axis_style(ax, preset: PresetArg = None) -> None:
    selected = _resolve_preset(preset)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#B8BEC5")
    ax.tick_params(width=0.6, length=2.5, color="#6B7280", labelsize=selected.body_pt)
    ax.xaxis.label.set_size(selected.body_pt)
    ax.yaxis.label.set_size(selected.body_pt)
    ax.xaxis.label.set_color("#243746")
    ax.yaxis.label.set_color("#243746")
    ax.title.set_size(selected.body_pt)
    legend = ax.get_legend()
    if legend is not None:
        for text in legend.get_texts():
            text.set_fontsize(selected.body_pt)
    ax.grid(axis="y", color="#E5E7EB", linewidth=0.5)
    ax.set_axisbelow(True)


def panel_label(ax, label: str, preset: PresetArg = None):
    if label not in {"a", "b", "c", "d"}:
        raise ValueError("panel labels must be lowercase a-d")
    selected = _resolve_preset(preset)
    return ax.text(
        -0.10,
        1.04,
        label,
        transform=ax.transAxes,
        fontsize=selected.panel_pt,
        fontweight="bold",
        color="#243746",
        va="bottom",
    )
