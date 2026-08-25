"""Content-aware layout primitives for editorial paper figures."""

from __future__ import annotations

from dataclasses import dataclass

from matplotlib.axes import Axes
from matplotlib.artist import Artist
from matplotlib.figure import Figure
from matplotlib.gridspec import GridSpec
from matplotlib.offsetbox import AnnotationBbox, TextArea
from matplotlib.patches import FancyBboxPatch
import matplotlib.pyplot as plt
from matplotlib.text import Text

from .fonts import validate_publication_fonts
from .qa import register_collision
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
            "fontfamily": "Charis SIL",
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


def editorial_figure(
    preset: VenuePreset,
    height_mm: float,
    headline: str,
    deck: str,
    *,
    rows: int,
    cols: int,
) -> tuple[Figure, GridSpec]:
    """Create a fixed canvas with a dedicated 13% figure-heading band."""

    if rows < 1 or cols < 1:
        raise ValueError("editorial grids require at least one row and one column")
    validate_publication_fonts()
    figure = plt.figure(figsize=preset.figsize(height_mm))
    header = figure.add_axes((0.08, 0.83, 0.90, 0.13), frameon=False)
    header.set_axis_off()
    title_artist = header.text(
        0.0,
        0.76,
        headline,
        transform=header.transAxes,
        color="#243746",
        fontfamily="Charis SIL",
        fontsize=preset.panel_pt + 2.0,
        fontweight="bold",
        ha="left",
        va="center",
    )
    deck_artist = header.text(
        0.0,
        0.24,
        deck,
        transform=header.transAxes,
        color="#243746",
        fontfamily="Charis SIL",
        fontsize=preset.body_pt,
        ha="left",
        va="center",
    )
    register_collision(figure, "figure-headline-deck", title_artist, deck_artist)
    bottom = max(0.08, 48.0 / (figure.get_figheight() * 72.0))
    left = max(0.08, 48.0 / (figure.get_figwidth() * 72.0))
    content = figure.add_gridspec(
        rows,
        cols,
        left=left,
        right=0.98,
        bottom=bottom,
        top=0.78,
        hspace=0.30,
        wspace=0.22,
    )
    return figure, content


def panel_heading(
    ax: Axes,
    label: str,
    title: str,
    deck: str,
    preset: VenuePreset,
) -> tuple[Text, Text, Text]:
    """Reserve and populate a physical title/deck band above one panel axis."""

    if len(label) != 1 or not label.islower() or not label.isalpha():
        raise ValueError("panel labels must be one lowercase letter")
    figure = ax.figure
    validate_publication_fonts()
    position = ax.get_position()
    figure_height_pt = figure.get_figheight() * 72.0
    figure_width_pt = figure.get_figwidth() * 72.0
    title_leading_pt = preset.panel_pt * 1.8
    deck_leading_pt = preset.body_pt * 1.6
    band_fraction = (title_leading_pt + deck_leading_pt + 3.0) / figure_height_pt
    if band_fraction >= position.height:
        raise ValueError("panel is too short to reserve its heading band")
    ax.set_position((position.x0, position.y0, position.width, position.height - band_fraction))

    title_y = position.y1
    deck_y = title_y - title_leading_pt / figure_height_pt
    title_x = position.x0 + (preset.panel_pt * 1.6) / figure_width_pt
    letter = figure.text(
        position.x0,
        title_y,
        label,
        color="#243746",
        fontfamily="Charis SIL",
        fontsize=preset.panel_pt,
        fontweight="bold",
        ha="left",
        va="top",
    )
    title_artist = figure.text(
        title_x,
        title_y,
        title,
        color="#243746",
        fontfamily="Charis SIL",
        fontsize=preset.panel_pt,
        fontweight="bold",
        ha="left",
        va="top",
    )
    deck_artist = figure.text(
        title_x,
        deck_y,
        deck,
        color="#243746",
        fontfamily="Charis SIL",
        fontsize=preset.body_pt,
        ha="left",
        va="top",
    )
    register_collision(figure, f"panel-{label}-letter-title", letter, title_artist)
    register_collision(figure, f"panel-{label}-letter-deck", letter, deck_artist)
    register_collision(figure, f"panel-{label}-title-deck", title_artist, deck_artist)
    return letter, title_artist, deck_artist
