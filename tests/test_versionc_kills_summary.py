"""The kill summary must not contradict the kills it just printed.

🔴 THE DEFECT THIS CATCHES SHIPPED. `verdict()` inserted the five settled kills with a
hardcoded ``"fired": False``, including **K-C7, whose own KILLS entry says
``"fired": True``**. The per-kill line printed `K-C7  FIRED` and the summary two lines later
printed `No kill fired.`

That is the worst possible failure mode for this file: a reader who scans the summary --
which is what a summary is for -- concludes Version C passed every kill, on the same output
that says K-C7 fired. The whole point of `analyse_versionc_form1.py` is that a registered
kill nothing evaluates is a paragraph; a kill evaluated and then dropped from the verdict is
worse, because it looks adjudicated.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ana():
    sys.path.insert(0, str(ROOT / "src"))
    spec = importlib.util.spec_from_file_location(
        "ana", ROOT / "scripts" / "analyse_versionc_form1.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["ana"] = m
    spec.loader.exec_module(m)
    return m


def test_kc7_is_reported_as_fired_in_the_verdict(ana):
    """The static table says fired; the verdict must agree with it."""
    assert ana.KILLS["K-C7"]["fired"] is True, "the source of truth says K-C7 fired"
    rows = json.loads((ROOT / "results" / "versionc-form1-s025.json").read_text())["rows"]
    v = ana.verdict(rows, 0.25, "versionb")
    assert v["kills"]["K-C7"]["fired"] is True, (
        "the verdict dropped K-C7's fired flag; the summary will say 'No kill fired' on a "
        "run where a kill fired")


def test_no_settled_kill_has_its_fired_flag_overwritten(ana):
    """General form: the verdict must never contradict KILLS for any settled kill."""
    rows = json.loads((ROOT / "results" / "versionc-form1-s025.json").read_text())["rows"]
    v = ana.verdict(rows, 0.25, "versionb")
    for k in ("K-C4", "K-C5", "K-C6", "K-C7", "K-C8"):
        assert v["kills"][k]["fired"] == ana.KILLS[k].get("fired", False), (
            f"{k}: verdict says fired={v['kills'][k]['fired']} but KILLS says "
            f"{ana.KILLS[k].get('fired', False)}")


def test_status_and_fired_never_disagree(ana):
    """A kill whose status reads FIRED must carry fired=True, at both sigmas."""
    for s, f in ((0.25, "versionc-form1-s025.json"), (0.10, "versionc-form1-s010.json")):
        rows = json.loads((ROOT / "results" / f).read_text())["rows"]
        v = ana.verdict(rows, s, "versionb")
        for name, k in v["kills"].items():
            if str(k.get("status", "")).upper() == "FIRED":
                assert k.get("fired") is True, (
                    f"sigma={s} {name}: status FIRED but fired={k.get('fired')}")


def test_the_freeze_citation_resolves_to_a_real_commit(ana):
    """The K-C7 reason cites the freeze commit. A citation nobody can follow is not evidence."""
    import re
    import subprocess
    reason = ana.KILLS["K-C7"]["reason"]
    shas = re.findall(r"\b[0-9a-f]{7,40}\b", reason)
    assert shas, "K-C7's reason must cite the freeze commit"
    for sha in shas:
        # REACHABLE FROM HEAD, not merely "an object that exists". Pre-gc, the purged
        # history's objects are all still present, so `cat-file -e` passes on the OLD
        # pre-rewrite SHA and the test would give a false green until someone runs gc.
        r = subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"],
                           cwd=ROOT, capture_output=True)
        assert r.returncode == 0, (
            f"K-C7 cites {sha}, which is not reachable from HEAD. The history rewrite that "
            f"purged p6-families.json changed every SHA from a59063b onward; docs were "
            f"repaired but this citation was not.")
