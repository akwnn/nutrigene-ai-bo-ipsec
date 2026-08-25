from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from matplotlib.figure import Figure


PROHIBITED_TOKENS = ("spade_random_plate2", "KF-3", "KF-4")


@dataclass(frozen=True)
class FigureBundle:
    figure_id: str
    figure: Figure
    panel_data: dict[str, Any]
    alt_text: str
    caption: str
    long_description: str
    headline: str = ""
    deck: str = ""
    layout_rows: tuple[tuple[str, ...], ...] = ()


def load_json(path: Path) -> dict[str, Any]:
    path = Path(path)
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected a top-level JSON object")
    return payload


def require_keys(record: dict[str, Any], keys: set[str], context: str) -> None:
    missing = keys - record.keys()
    if missing:
        raise ValueError(f"{context}: missing keys {sorted(missing)}")


def assert_no_prohibited_content(value: Any) -> None:
    encoded = json.dumps(value, sort_keys=True)
    found = [token for token in PROHIBITED_TOKENS if token in encoded]
    if found:
        raise ValueError(f"prohibited boundary evidence present: {found}")


def sha256_file(path: Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
