"""Fail-closed adjudicator for the frozen variance-corrected DC2 protocol."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import analyse_dc_doe_certificate as historical
from scripts import run_dc2_doe_certificate as dc2


def analyse(path: Path) -> bool:
    protocol = dc2.DC2Protocol()
    payload = json.loads(path.read_text())
    dc2.validate_artifact(
        payload,
        protocol,
        require_complete=True,
        expected_spec_sha256=dc2._sha256(dc2.SPEC),
        expected_runner_sha256=dc2._sha256(Path(dc2.__file__)),
    )

    cells, regret = historical.load([str(path)])
    grid = sorted(protocol.c_grid)
    print("=== DC2 variance-corrected adjudication ===")
    print(
        f"fresh seeds={protocol.seed_start}..{protocol.seed_stop - 1} "
        f"jobs={protocol.expected_jobs} rows={protocol.expected_rows}"
    )
    print("All rows passed exact-grid, finite-value, clean-source, and digest validation.\n")
    print(f"{'arm':<16}{'rounds':>7}{'c*':>6}{'answered':>11}{'contained':>11}"
          f"{'contain':>9}{'LB':>9}  certifies?")

    verdict: dict[str, bool] = {}
    rounds = dict(protocol.arms)
    for arm, arm_rounds in protocol.arms:
        c_star, answered, contained, answer_rate = historical.best_c(
            cells, arm, historical.TARGET_P, grid
        )
        if c_star is None:
            answered, contained, answer_rate, total = historical.cert(
                cells, arm, historical.TARGET_P, grid[0]
            )
            containment = f"{contained / answered:.4f}" if answered else "n/a"
            verdict[arm] = False
            print(
                f"{arm:<16}{arm_rounds:>7}{'none':>6}{f'{answered}/{total}':>11}"
                f"{contained:>11}{containment:>9}"
                f"{historical.cp_lower(contained, answered):>9.4f}  no"
            )
        else:
            _n, _k, _rate, total = historical.cert(
                cells, arm, historical.TARGET_P, c_star
            )
            verdict[arm] = True
            print(
                f"{arm:<16}{arm_rounds:>7}{c_star:>6g}{f'{answered}/{total}':>11}"
                f"{contained:>11}{contained / answered:>9.4f}"
                f"{historical.cp_lower(contained, answered):>9.4f}  YES"
            )

    confirmed = (
        verdict.get("spade") is True
        and verdict.get("doe") is False
        and verdict.get("doe_unscreened") is False
    )
    print("\nPRIMARY VERDICT: " + (
        "CONFIRMED — SPADE passes; both DoE arms fail the registered certificate gate"
        if confirmed else
        "NOT CONFIRMED — the registered three-part conjunction did not hold"
    ))

    print("\nSecondary regret estimates (SPADE minus comparator; positive is worse):")
    for other in ("doe", "doe_unscreened"):
        keys = sorted(
            {(family, seed) for arm, family, seed in regret if arm == "spade"}
            & {(family, seed) for arm, family, seed in regret if arm == other}
        )
        differences = [
            regret[("spade", family, seed)] - regret[(other, family, seed)]
            for family, seed in keys
        ]
        mean, lo, hi, p_value = historical.boot(differences, seed=1)
        print(
            f"  spade vs {other}: n={len(differences)} {mean:+.4f} "
            f"CI[{lo:+.4f},{hi:+.4f}] p={p_value:.4f}"
        )
    return confirmed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        analyse(args.input)
    except Exception as exc:
        print(f"REFUSED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
