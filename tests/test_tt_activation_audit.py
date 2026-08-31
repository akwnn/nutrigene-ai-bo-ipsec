"""TT activation predicate and committed audit regression checks."""
import json
from pathlib import Path

import torch

from boec.certstraddle import contour_target_is_active


def test_target_is_active_only_inside_adjusted_margin_range():
    adjusted = torch.tensor([-0.4, 0.1, 0.7])
    assert contour_target_is_active(adjusted, theta=0.0)
    assert not contour_target_is_active(adjusted, theta=-0.4)
    assert not contour_target_is_active(adjusted, theta=0.7)


def test_committed_audit_has_registered_totals():
    path = Path(__file__).parents[1] / "results" / "tt-activation-audit.json"
    if not path.exists():
        return
    data = json.loads(path.read_text())
    assert data["status"] == "COMPLETE"
    assert data["active_rounds"] == 206
    assert data["total_rounds"] == 640
    assert data["campaigns_active_all_rounds"] == 20
    assert data["total_campaigns"] == 160


def test_audit_records_one_unique_cell_per_campaign_round():
    path = Path(__file__).parents[1] / "results" / "tt-activation-audit.json"
    if not path.exists():
        return
    rows = json.loads(path.read_text())["records"]
    keys = [(r["family"], r["seed"], r["round"]) for r in rows]
    assert len(keys) == len(set(keys)) == 640
