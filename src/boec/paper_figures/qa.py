"""Renderer-level quality contracts for publication figures."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from matplotlib.artist import Artist
from matplotlib.font_manager import findfont
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox
from matplotlib.text import Text
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.container import BarContainer


@dataclass(frozen=True)
class GeometryRegistration:
    label: str
    content: Artist
    container: Artist
    padding_pt: float


@lru_cache(maxsize=1)
def resolved_publication_font() -> Path:
    """Return the exact Arial file used for publication rendering."""

    try:
        return Path(findfont("Arial", fallback_to_default=False)).resolve()
    except ValueError as exc:
        raise RuntimeError("Arial is required for publication figure rendering") from exc


def register_artist(
    figure: Figure,
    label: str,
    content: Artist,
    container: Artist,
    *,
    padding_pt: float = 2.0,
) -> None:
    """Register content that must remain inside a semantic container."""

    registrations = getattr(figure, "_paper_geometry", None)
    if registrations is None:
        registrations = []
        setattr(figure, "_paper_geometry", registrations)
    registrations.append(GeometryRegistration(label, content, container, padding_pt))


def assert_registered_geometry(figure: Figure) -> None:
    """Assert registered text fits its container with physical point padding."""

    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    for registration in getattr(figure, "_paper_geometry", []):
        outer = registration.container.get_window_extent(renderer)
        pad = renderer.points_to_pixels(registration.padding_pt)
        inner = Bbox.from_extents(
            outer.x0 + pad,
            outer.y0 + pad,
            outer.x1 - pad,
            outer.y1 - pad,
        )
        content = registration.content.get_window_extent(renderer)
        if not (
            inner.contains(*content.get_points()[0])
            and inner.contains(*content.get_points()[1])
        ):
            raise AssertionError(
                f"{registration.label}: content {content.bounds} escapes padded container {inner.bounds}"
            )


def assert_label_clearance(figure: Figure, *, padding_pt: float = 0.5) -> None:
    """Reject clipped or colliding labels after layout at the current render DPI.

    Checks text against text, data markers, data lines and visible spines.
    Background grids, intentional enclosing boxes and table cells are excluded;
    their containment is checked separately by ``assert_registered_geometry``.
    Visual review of the exported files remains required.
    """
    figure.canvas.draw()
    renderer = figure.canvas.get_renderer()
    pad = renderer.points_to_pixels(padding_pt)
    axes = list(figure.axes)
    for axis in list(axes):
        axes.extend(axis.child_axes)
    hidden_text = set()
    for axis in axes:
        if not axis.axison:
            hidden_text.update(axis.xaxis.findobj(match=Text))
            hidden_text.update(axis.yaxis.findobj(match=Text))
        for coordinate in (axis.xaxis, axis.yaxis):
            lower, upper = sorted(coordinate.get_view_interval())
            for tick in coordinate.get_major_ticks() + coordinate.get_minor_ticks():
                if not lower <= tick.get_loc() <= upper:
                    hidden_text.update((tick.label1, tick.label2))
    labels = []
    errors = []
    for artist in figure.findobj(match=Text):
        if artist in hidden_text or not artist.get_visible() or not artist.get_text().strip():
            continue
        box = artist.get_window_extent(renderer)
        if not all(figure.bbox.contains(*corner) for corner in box.get_points()):
            errors.append(f"clipped label {artist.get_text()!r}")
        labels.append((artist, box))
    for index, (first, box) in enumerate(labels):
        for second, other in labels[index + 1:]:
            if box.padded(pad).overlaps(other):
                errors.append(f"labels overlap: {first.get_text()!r} / {second.get_text()!r}")
    obstacles = []
    for axis in axes:
        for container in axis.containers:
            if isinstance(container, BarContainer):
                obstacles.extend((patch.get_path().transformed(patch.get_transform()), axis)
                                 for patch in container.patches if patch.get_visible() and patch.get_width())
        for line in list(axis.lines) + ([s for s in axis.spines.values() if s.get_visible()] if axis.axison else []):
            if line.get_visible():
                obstacles.append((line.get_path().transformed(line.get_transform()), axis))
        for collection in axis.collections:
            if not collection.get_visible():
                continue
            if isinstance(collection, LineCollection):
                obstacles.extend((p.transformed(collection.get_transform()), axis) for p in collection.get_paths())
            elif isinstance(collection, PathCollection):
                offsets = collection.get_offset_transform().transform(collection.get_offsets())
                transforms = collection.get_transforms()
                paths = collection.get_paths()
                for i, offset in enumerate(offsets):
                    if not paths:
                        continue
                    from matplotlib.transforms import Affine2D
                    transform = Affine2D(transforms[i % len(transforms)]) if len(transforms) else Affine2D()
                    path = paths[i % len(paths)].transformed(transform.translate(*offset))
                    obstacles.append((path, axis))
    for label, box in labels:
        for path, axis in obstacles:
            # Artists outside the view are clipped by Matplotlib.
            if not path.intersects_bbox(axis.bbox, filled=False):
                continue
            if path.intersects_bbox(box.padded(pad), filled=True):
                errors.append(f"label touches plotted mark or spine: {label.get_text()!r}")
                break
    if errors:
        raise AssertionError("\n".join(errors))


def _relative_luminance(colour: str) -> float:
    value = colour.removeprefix("#")
    if len(value) != 6:
        raise ValueError("colours must use six-digit hexadecimal notation")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Return the WCAG contrast ratio for two hexadecimal colours."""

    first, second = _relative_luminance(foreground), _relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)
