"""Packaged publication font assets and explicit Matplotlib registration."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
import json
from pathlib import Path

from matplotlib import font_manager


@dataclass(frozen=True)
class FontAssets:
    text_regular: Path
    text_bold: Path
    text_italic: Path
    text_bold_italic: Path
    math_regular: Path


def _font_root() -> Path:
    return Path(str(files("boec.paper_figures").joinpath("fonts")))


@lru_cache(maxsize=1)
def register_publication_fonts() -> FontAssets:
    """Register the exact packaged font files used by publication figures."""

    root = _font_root()
    assets = FontAssets(
        root / "CharisSIL-Regular.ttf",
        root / "CharisSIL-Bold.ttf",
        root / "CharisSIL-Italic.ttf",
        root / "CharisSIL-BoldItalic.ttf",
        root / "STIXMath-Regular.otf",
    )
    for path in dataclasses.astuple(assets):
        if not path.is_file():
            raise RuntimeError(f"required publication font is missing: {path}")
        font_manager.fontManager.addfont(path)
    return assets


def validate_publication_fonts() -> FontAssets:
    """Fail unless every publication family/style resolves to its packaged file."""

    assets = register_publication_fonts()
    lookups = (
        ("Charis SIL", "normal", "normal", assets.text_regular),
        ("Charis SIL", "normal", "bold", assets.text_bold),
        ("Charis SIL", "italic", "normal", assets.text_italic),
        ("Charis SIL", "italic", "bold", assets.text_bold_italic),
        ("STIX Math", "normal", "normal", assets.math_regular),
    )
    for family, style, weight, expected in lookups:
        properties = font_manager.FontProperties(
            family=[family], style=style, weight=weight
        )
        resolved = Path(
            font_manager.findfont(properties, fallback_to_default=False)
        ).resolve()
        expected = expected.resolve()
        if resolved != expected:
            raise RuntimeError(
                f"required publication font {family} {style}/{weight} resolved "
                f"outside packaged assets: expected {expected}, got {resolved}"
            )
    return assets


def font_manifest() -> dict[str, object]:
    """Return the recorded sources and SHA-256 digests for packaged fonts."""

    path = _font_root() / "font-assets.json"
    if not path.is_file():
        raise RuntimeError(f"publication font manifest is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"publication font manifest must contain an object: {path}")
    return payload
