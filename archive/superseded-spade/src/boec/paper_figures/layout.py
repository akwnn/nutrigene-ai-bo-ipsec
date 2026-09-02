"""Content-aware layout primitives for editorial paper figures."""

from __future__ import annotations

from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.artist import Artist
from matplotlib.offsetbox import AnnotationBbox, TextArea
from matplotlib.patches import FancyBboxPatch

from .style import VenuePreset


@dataclass(frozen=True)
class EditorialText:
    """A content-sized text card and the artists used for geometry QA."""

    annotation: AnnotationBbox
    text: Artist
    patch: FancyBboxPatch


def content_box(
    ax: Axes,
    xy: tuple[float, float],
    text: str,
    preset: VenuePreset,
    *,
    facecolor: str = "#E8F1F8",
    edgecolor: str = "#243746",
    boxstyle: str = "round,pad=0.28,rounding_size=0.08",
    dashed: bool = False,
    fontweight: str = "normal",
    box_alignment: tuple[float, float] = (0.5, 0.5),
) -> EditorialText:
    """Place a node whose frame grows from the rendered text dimensions."""

    text_area = TextArea(
        text,
        textprops={
            "color": "#243746",
            "fontsize": preset.body_pt,
            "fontfamily": "Arial",
            "fontweight": fontweight,
            "ha": "center",
            "linespacing": 1.15,
        },
    )
    annotation = AnnotationBbox(
        text_area,
        xy,
        xycoords=ax.transAxes,
        box_alignment=box_alignment,
        frameon=True,
        pad=0.35,
        bboxprops={
            "boxstyle": boxstyle,
            "facecolor": facecolor,
            "edgecolor": edgecolor,
            "linewidth": 0.8,
            "linestyle": "--" if dashed else "-",
        },
    )
    ax.add_artist(annotation)
    # Register the TextArea rather than its internal Text artist: Matplotlib
    # applies the final offset at the container level, so this is the rendered
    # content extent used for collision and containment checks.
    return EditorialText(annotation, text_area, annotation.patch)
