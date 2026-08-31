"""Fail-closed verification for SPADE's current numerical and semantic claims."""
from __future__ import annotations

import hashlib
import json
import random
import statistics as st
import sys
from pathlib import Path

from scipy.stats import beta, spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import analyse_dc_doe_certificate as historical_dc
from scripts import analyse_tau_sweep as tau_analysis
from scripts import analyse_tt_theta_tau as tt_analysis
from scripts import audit_tt_activation
from scripts import run_dc2_doe_certificate as dc2

TT_ARMS = ("spade", "spade_tau", "qlognei")
TT_P_GRID = (0.70, 0.30)
TT_C_GRID = (1.0, 1.5, 2.0, 3.0)
HISTORICAL_DC_HASHES = {
    "dc-ackley.json": "70860f8d668bcfc1ccef8166c29ab8d2d67ee17990a96d58602d5efe8815502e",
    "dc-hartmann6.json": "5ec0fa12b74d269694cc08c5548213079ef37d2fb4d0ed6e148a0940a17d28c3",
    "dc-hill.json": "d61c69aff26590fab9f54f2b880cc6cbecebe53e040b296b178b5cf3af19bda6",
    "dc-levy.json": "408b633fc13feb3e6b5126043e894774c444b702422a0be4a0797a10d800592b",
    "dc-rosenbrock.json": "db511648fed6b9e850c8e470697afde1800416c1fe3d2087f9b167a8ca798339",
}


class Checks:
    def __init__(self) -> None:
        self.results: list[bool] = []

    def require(self, name: str, condition: bool, detail: str = "") -> None:
        good = bool(condition)
        self.results.append(good)
        suffix = f" — {detail}" if detail else ""
        print(f"  [{'OK' if good else 'MISMATCH'}] {name}{suffix}")

    def close(self, name: str, got: float, want: float, tolerance: float) -> None:
        good = abs(float(got) - float(want)) <= tolerance
        self.results.append(good)
        print(
            f"  [{'OK' if good else 'MISMATCH'}] {name}: "
            f"expected={want} recomputed={float(got):.6f} tol={tolerance}"
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_rows(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for path in paths:
        raw = json.loads(path.read_text())
        rows.extend(raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw)
    return rows


def _bootstrap(values: list[float], seed: int, n: int = 8000):
    rng = random.Random(seed)
    means = sorted(
        sum(values[rng.randrange(len(values))] for _ in values) / len(values)
        for _ in range(n)
    )
    le = sum(value <= 0 for value in means) / n
    ge = sum(value >= 0 for value in means) / n
    return (
        st.mean(values),
        means[int(0.025 * n)],
        means[int(0.975 * n)],
        min(1.0, 2 * min(le, ge)),
    )


def _verify_tt(checks: Checks) -> None:
    print("TT — exact grid, registered statistics, multiplicity, activation")
    paths = [ROOT / "results" / f"tt-{family}.json" for family in tt_analysis.FAMILIES]
    checks.require("all five TT files exist", all(path.is_file() for path in paths))
    rows = _load_rows(paths)
    observed: set[tuple[str, str, int, float, float]] = set()
    duplicate = False
    regret_values: dict[tuple[str, str, int], set[float]] = {}
    for row in rows:
        key = (
            str(row["arm"]),
            str(row["family"]),
            int(row["seed"]),
            float(row["p_value"]),
            float(row["inflation_c"]),
        )
        duplicate |= key in observed
        observed.add(key)
        regret_values.setdefault(key[:3], set()).add(float(row["regret"]))
    expected = {
        (arm, family, seed, p_value, inflation_c)
        for arm in TT_ARMS
        for family in tt_analysis.FAMILIES
        for seed in range(32)
        for p_value in TT_P_GRID
        for inflation_c in TT_C_GRID
    }
    checks.require("TT has no duplicate cells", not duplicate)
    checks.require("TT exact 3,840-cell grid", observed == expected,
                   f"observed={len(observed)} expected={len(expected)}")
    checks.require("TT regret is invariant across scoring cells",
                   all(len(values) == 1 for values in regret_values.values()))

    cells, regret = tt_analysis.load([str(path) for path in paths])
    spade_volumes = tt_analysis.vols(cells, "spade", tt_analysis.TARGET_P)
    tau_volumes = tt_analysis.vols(cells, "spade_tau", tt_analysis.TARGET_P)
    paired = sorted(set(spade_volumes) & set(tau_volumes))
    mean, lo, hi, p_value = tt_analysis.boot(
        [tau_volumes[key] - spade_volumes[key] for key in paired], seed=1
    )
    checks.close("TT volume mean", mean, 0.000425, 0.0000006)
    checks.close("TT volume CI lower", lo, -0.000022, 0.0000006)
    checks.close("TT volume CI upper", hi, 0.000875, 0.0000006)
    checks.close("TT volume p", p_value, 0.0645, 0.0002)
    checks.require("TT volume conclusion is inconclusive", lo <= 0 <= hi)

    regret_keys = sorted(
        {(family, seed) for arm, family, seed in regret if arm == "spade"}
        & {(family, seed) for arm, family, seed in regret if arm == "spade_tau"}
    )
    regret_result = tt_analysis.boot(
        [regret[("spade_tau", family, seed)] - regret[("spade", family, seed)]
         for family, seed in regret_keys],
        seed=3,
    )
    checks.close("TT regret mean", regret_result[0], 0.0301, 0.00006)
    checks.close("TT regret CI lower", regret_result[1], 0.0169, 0.00006)
    checks.close("TT regret CI upper", regret_result[2], 0.0450, 0.00006)
    checks.require("TT regret noninferiority fails", regret_result[2] > tt_analysis.SESOI)
    checks.require("TT regret lower endpoint does not exceed SESOI",
                   regret_result[1] < tt_analysis.SESOI)

    family_raw: dict[str, float] = {}
    for family in tt_analysis.FAMILIES:
        keys = [key for key in paired if key[0] == family]
        family_raw[family] = tt_analysis.boot(
            [tau_volumes[key] - spade_volumes[key] for key in keys], seed=2
        )[3]
    adjusted = tt_analysis.holm_adjust(family_raw)
    checks.require("no TT family survives Holm correction",
                   all(value >= 0.05 for value in adjusted.values()))
    checks.close("smallest Holm-adjusted family p", min(adjusted.values()), 0.06125, 0.0002)

    activation_path = ROOT / "results" / "tt-activation-audit.json"
    activation = json.loads(activation_path.read_text())
    audit_tt_activation.validate_rows(
        activation["rows"],
        tuple(activation["families"]),
        range(activation["seed_start"], activation["seed_stop"]),
        activation["adaptive_rounds"],
    )
    summary = audit_tt_activation.summarize_rows(
        activation["rows"],
        tuple(activation["families"]),
        range(activation["seed_start"], activation["seed_stop"]),
        activation["adaptive_rounds"],
    )
    checks.require("TT activation artifact is COMPLETE", activation["status"] == "COMPLETE")
    checks.require("TT activation source was clean", activation["source_dirty"] is False)
    checks.close("TT active rounds", summary["active_rounds"], 206, 0)
    checks.close("TT total rounds", summary["total_rounds"], 640, 0)
    checks.close("TT fully active campaigns", summary["campaigns_active_all_rounds"], 20, 0)
    checks.require("TT activation spec digest matches",
                   activation["spec_sha256"] == _sha256(audit_tt_activation.SPEC))
    checks.require("TT activation script digest matches",
                   activation["script_sha256"] == _sha256(Path(audit_tt_activation.__file__)))


def _verify_historical_dc(checks: Checks) -> None:
    print("\nHistorical DC — immutable bytes, reproducible calculation, bounded use")
    directory = ROOT / "results" / "historical-dc-constant-yvar"
    paths = [directory / name for name in HISTORICAL_DC_HASHES]
    for path in paths:
        checks.require(f"historical hash {path.name}",
                       _sha256(path) == HISTORICAL_DC_HASHES[path.name])
    cells, _regret = historical_dc.load([str(path) for path in paths])
    for arm, expected_answered, expected_contained in (
        ("doe", 122, 85),
        ("doe_unscreened", 134, 77),
        ("spade", 66, 66),
        ("qlognei", 59, 58),
    ):
        answered, contained, _rate, total = historical_dc.cert(
            cells, arm, historical_dc.TARGET_P, 1.0
        )
        checks.close(f"historical {arm} answered", answered, expected_answered, 0)
        checks.close(f"historical {arm} contained", contained, expected_contained, 0)
        checks.close(f"historical {arm} total", total, 160, 0)

    paper = (ROOT / "docs" / "SPADE-PAPER-ARGUMENT.md").read_text().lower()
    conclusions = (ROOT / "docs" / "SPADE-CONCLUSIONS-2026-08-29.md").read_text().lower()
    for label, text in (("paper", paper), ("conclusions", conclusions)):
        checks.require(f"{label} labels DC historical", "historical" in text)
        checks.require(f"{label} labels DC not confirmatory", "not confirmatory" in text)
        checks.require(f"{label} requires variance-corrected replication",
                       "variance-corrected replication" in text)
        checks.require(f"{label} uses no detectable regret difference",
                       "no detectable regret difference" in text)
    checks.require("paper does not claim a BO tie", "ties bo" not in paper)
    checks.require("paper does not claim unique trustworthy method",
                   "only method that returns an operating region you can trust" not in paper)

    dc2_path = ROOT / "results" / "dc2-sweep.json"
    if dc2_path.exists():
        payload = json.loads(dc2_path.read_text())
        dc2.validate_artifact(
            payload,
            dc2.DC2Protocol(),
            require_complete=True,
            expected_spec_sha256=dc2._sha256(dc2.SPEC),
            expected_runner_sha256=dc2._sha256(Path(dc2.__file__)),
        )
        checks.require("DC2 artifact passes confirmatory validation", True)
    else:
        checks.require("no unrun DC2 result is implied by the docs",
                       "has not been run" in paper and "has not been run" in conclusions)


def _verify_standing_claims(checks: Checks) -> None:
    print("\nStanding LC/TAU claims")
    lc_rows = _load_rows(sorted((ROOT / "results").glob("lc-*.json")))
    lc = {}
    for row in lc_rows:
        value = row.get("regret")
        if value is not None and not (isinstance(value, float) and value != value):
            lc[(row["arm"], row["rounds"], row["family"], row["seed"])] = float(value)
    paired = [
        (family, seed)
        for arm, rounds, family, seed in lc
        if (arm, rounds) == ("spade", 5) and ("qlognei", 10, family, seed) in lc
    ]
    differences = [
        lc[("spade", 5, family, seed)] - lc[("qlognei", 10, family, seed)]
        for family, seed in paired
    ]
    mean, lo, hi, _p = _bootstrap(differences, seed=7)
    checks.close("LC regret mean", mean, 0.0016, 0.0004)
    checks.close("LC regret CI lower", lo, -0.0184, 0.002)
    checks.close("LC regret CI upper", hi, 0.0208, 0.002)
    checks.close("LC paired n", len(differences), 160, 0)

    tau_paths = [ROOT / "results" / f"tau-{family}.json" for family in tau_analysis.FAMILIES]
    cells, difficulty = tau_analysis.load([str(path) for path in tau_paths])
    families = sorted({key[1] for key in cells})
    p_values = sorted({key[3] for key in cells}, reverse=True)
    margins, answer_rates = [], []
    for family in families:
        for p_value in p_values:
            _lb, _n, answer_rate = tau_analysis.pooled(
                cells,
                lambda key, family=family, p_value=p_value:
                    key[1] == family and key[3] == p_value and key[4] == 1.0,
            )
            margin = difficulty.get((family, p_value), float("nan"))
            if margin == margin:
                margins.append(margin)
                answer_rates.append(answer_rate)
    rho, _p = spearmanr(margins, answer_rates)
    checks.close("TAU margin/sd Spearman rho", rho, 0.9801, 0.0005)
    checks.close("TAU correlation cells", len(margins), 25, 0)

    answered = contained = 0
    for (arm, family, _seed, p_value, inflation_c), (nonempty, good, _volume) in cells.items():
        if arm == "spade" and family == "hill" and p_value == 0.70 and inflation_c == 1.0:
            if nonempty:
                answered += 1
                contained += bool(good)
    lower = 0.0 if contained == 0 else float(
        beta.ppf(0.05, contained, answered - contained + 1)
    )
    checks.close("hill p=0.70 answered", answered, 40, 0)
    checks.close("hill p=0.70 contained", contained, 40, 0)
    checks.close("hill p=0.70 containment lower bound", lower, 0.9278, 0.0002)


def main() -> int:
    checks = Checks()
    try:
        _verify_tt(checks)
        _verify_historical_dc(checks)
        _verify_standing_claims(checks)
    except Exception as exc:
        print(f"  [MISMATCH] verifier raised {type(exc).__name__}: {exc}")
        checks.results.append(False)
    passed = sum(checks.results)
    total = len(checks.results)
    print(f"\n===== {passed}/{total} current checks pass =====")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
