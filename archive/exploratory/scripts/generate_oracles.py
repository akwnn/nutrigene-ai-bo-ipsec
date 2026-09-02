"""Generate the Phase 1 instance ensemble.

Writes one parquet of sampled points per dimension plus a JSON sidecar per instance
and an audit JSON per dimension. The audit carries the acceptance rate and the
accepted-vs-nominal marginals — any acceptance rule truncates the stated draws, and
the point of reporting it is that the truncation is declared rather than silent.

Usage::

    python scripts/generate_oracles.py --dims 6 8 --n-instances 25
    python scripts/generate_oracles.py --dims 6 --accept-on formula --tag v6compare
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from boec.evaluators import SyntheticEvaluator  # noqa: E402
from boec.oracles import HillOracle, SamplerConfig, generate_ensemble  # noqa: E402
from boec.space import MetricIdentity  # noqa: E402

METRIC = MetricIdentity(
    name="synthetic_response", unit="normalized", protocol_version="phase1-v1"
)


def build(args: argparse.Namespace) -> None:
    root = Path(args.out)

    for dim in args.dims:
        cfg = SamplerConfig(
            interaction=args.interaction,
            accept_on=args.accept_on,
            draw_order=args.draw_order,
            accept_floor=args.accept_floor,
            formula_prefloor=args.formula_prefloor,
            gamma_max=args.gamma_max,
            n_active=args.n_active,
            active_share=args.active_share,
        )
        # Version-stamped output directory. Two oracle versions sharing one namespace is
        # exactly the silent-mixing failure `oracle_version` exists to prevent -- the
        # field catches it on read, but the layout should not invite it in the first place.
        out = root / cfg.version()
        (out / "sidecars").mkdir(parents=True, exist_ok=True)

        insts, audit = generate_ensemble(
            dim, args.n_instances, cfg, seed0=args.seed0,
            max_candidates=args.max_candidates,
        )
        print(
            f"d={dim}: accepted {audit['accepted']}/{audit['requested']} from "
            f"{audit['candidates_tried']} candidates ({audit['acceptance_rate']*100:.1f}%)"
            f" | true depth med {audit['true_depth_median']:.4f} min "
            f"{audit['true_depth_min']:.4f} | influence ratio "
            f"{audit['influence_ratio_median']:.1f}x | resamples/factor "
            f"{audit['mean_factor_resamples']:.1f}"
        )

        rows = []
        rng = np.random.default_rng(args.seed0 + 5000 + dim)
        for inst in insts:
            oracle = HillOracle(inst)
            ev = SyntheticEvaluator(
                oracle, METRIC, sigma_rel=args.sigma_rel,
                sigma_add=args.sigma_add, seed=inst.seed,
            )
            X = rng.uniform(0.0, 1.0, (args.n_points, dim))
            y_true = ev.evaluate_true(X)
            y_obs, y_var = ev.evaluate(X)
            frame = {
                "instance_id": inst.instance_id,
                "oracle_version": inst.oracle_version,
                "seed": inst.seed,
                "dim": dim,
            }
            for j in range(dim):
                frame[f"x_{j}"] = X[:, j]
            frame["y_true"] = y_true[:, 0]
            frame["y_observed"] = y_obs[:, 0]
            frame["y_var"] = y_var[:, 0]
            frame.update(METRIC.as_dict())
            rows.append(pd.DataFrame(frame))
            # `in_subbox` is deliberately absent: it is an E4 construct derived at
            # experiment level, not a property of the instance.
            (out / "sidecars" / f"{inst.instance_id}.json").write_text(
                json.dumps(inst.sidecar(), indent=2)
            )

        if rows:
            pd.concat(rows, ignore_index=True).to_parquet(
                out / f"instances_d{dim}{args.tag}.parquet", index=False
            )
        (out / f"audit_d{dim}{args.tag}.json").write_text(json.dumps(audit, indent=2))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dims", type=int, nargs="+", default=[6, 8])
    p.add_argument("--n-instances", type=int, default=25)
    p.add_argument("--n-points", type=int, default=48)
    p.add_argument("--seed0", type=int, default=1000)
    p.add_argument("--out", default="data/oracles")
    p.add_argument("--tag", default="")
    p.add_argument("--interaction", default="peak_modulation",
                   choices=["peak_modulation", "product"])
    p.add_argument("--accept-on", default="true_depth", choices=["true_depth", "formula"])
    p.add_argument("--draw-order", default="w_first", choices=["w_first", "delta_first"])
    p.add_argument("--accept-floor", type=float, default=0.1083)  # 3*0.25/sqrt(48)
    p.add_argument("--formula-prefloor", type=float, default=0.120)
    p.add_argument("--gamma-max", type=float, default=1.0)
    p.add_argument("--n-active", type=int, default=4)
    p.add_argument("--active-share", type=float, default=0.90)
    p.add_argument("--sigma-rel", type=float, default=0.25)  # primary; 0.10 is the optimistic bound
    p.add_argument("--sigma-add", type=float, default=0.01)
    p.add_argument("--max-candidates", type=int, default=None)
    build(p.parse_args())


if __name__ == "__main__":
    main()
