"""Renderer-level quality contracts for publication figures."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from matplotlib.artist import Artist
from matplotlib.font_manager import findfont
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox


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
