"""PF2 — inversion, the closed form, acceptance rate, and the delta_max distribution.

OWNERSHIP: Person A. Reproduce with `python scripts/preflight_pf2.py`.

Four numbers, all on A's own module, all of which void every downstream result if
wrong. The suite in `tests/test_oracles.py` asserts each of them; this script reports
the *distributions* the assertions reduce to a pass/fail, because "the acceptance rate
is fine" and "the acceptance rate is 0.104%" are both consistent with a green test that
only checks the instances which survived.

Number 3 is the one that changed the design. Under the specification as written the
acceptance rate at d=8 is 0.104% -- 965 draws per accepted instance -- and the ensemble
that results is an undeclared truncation of the nominal parameter ranges. Both numbers
are reported here so the fix has something to be measured against.
"""

from __future__ import annotations

import numpy as np

from boec.oracles import (
    SHIPPED_CONFIG,
    HillOracle,
    SamplerConfig,
    accept_instance,
    delta_max,
    depth_of_r,
    invert_r,
    load_ensemble,
    propose_instance,
)

N_TRIALS = 2000
RNG = np.random.default_rng(20260807)


def q1_verification_case() -> None:
    print(f"\n{'=' * 84}\nPF2.1 · the inversion verification case\n{'=' * 84}")
    r = float(invert_r(0.4, 2.0, 0.414))
    s = r ** (2.0 / 2.0)
    back = float(depth_of_r(0.4, 2.0, r))
    ok = abs(s - 3.9917) < 5e-4
    print(f"  (x*=0.4, n=2, delta=0.414)  ->  s = {s:.4f}   (spec says 3.9917)   "
          f"{'OK' if ok else '*** MISMATCH ***'}")
    print(f"  r = s^(2/n) = {r:.4f}   (recovers r = 4)")
    print(f"  round trip: depth(r) = {back:.6f}  vs  0.414   err {abs(back - 0.414):.2e}")

    errs = []
    for _ in range(N_TRIALS):
        xs, n = RNG.uniform(0.25, 0.55), RNG.uniform(1.0, 3.0)
        dm = float(delta_max(xs, n))
        d = RNG.uniform(0.3, 0.9) * dm
        errs.append(abs(float(depth_of_r(xs, n, float(invert_r(xs, n, d)))) - d))
    print(f"  round trip over {N_TRIALS} random draws: max |error| = {max(errs):.2e}")


def q2_closed_form_on_a_beta_zero_variant() -> None:
    """With no interaction the landscape is separable, so the joint optimum is exactly
    the vector of per-factor peaks sqrt(EC50*IC50). A known answer, which is what makes
    it the strongest test available."""
    print(f"\n{'=' * 84}\nPF2.2 · closed form on a gamma = 0 variant\n{'=' * 84}")
    worst_x, worst_v = 0.0, 0.0
    for inst in load_ensemble(dim=6) + load_ensemble(dim=8):
        flat = replace_gamma_with_zeros(inst)
        orc = HillOracle(flat)
        x_num, v_num = orc.locate_optimum(n_restarts=24, seed=0)
        x_closed = np.sqrt(flat.ec50 * flat.ic50)
        worst_x = max(worst_x, float(np.abs(x_num - x_closed).max()))
        worst_v = max(worst_v, abs(v_num - 1.0))
    print(f"  50 instances, gamma forced to zero")
    print(f"  max |numerical argmax - sqrt(EC50*IC50)| = {worst_x:.3e}")
    print(f"  max |f(x_opt) - 1|                       = {worst_v:.3e}")
    print(f"  {'OK' if worst_x < 1e-4 and worst_v < 1e-9 else '*** MISMATCH ***'}")


def replace_gamma_with_zeros(inst):
    from dataclasses import replace
    return replace(inst, gamma=np.zeros_like(inst.gamma))


def q3_acceptance_rate() -> None:
    """Two arms, deliberately measured at different sample sizes.

    `propose_instance` costs 0.32 ms; `accept_instance` costs ~1 s, because it runs a
    multistart optimum search plus 2d boundary-face solves plus a dense positivity
    sample. So the two arms are sized to what each actually needs:

    * **v6** is a rejection sampler and the constraint that does the rejecting is the
      closed-form depth `min_i w_i*delta_i >= 0.045`. That is arithmetic, so it can be
      measured on 20,000 draws and the resulting rate is precise to ~0.1%. The
      expensive sub-checks cannot rescue an instance the floor has already failed.
    * **v8** accepts on the *numerically computed* depth, which is the expensive path
      and cannot be shortcut. 40 seeds per dimension, with the binomial interval shown
      so the imprecision is visible rather than implied.
    """
    print(f"\n{'=' * 84}\nPF2.3 · instance acceptance rate\n{'=' * 84}")

    # The v6 draw is written out here rather than obtained from `propose_instance`,
    # and the distinction is the whole point of the measurement. The shipped sampler
    # draws w FIRST and then samples delta from [floor/w_i, 0.9*delta_max], so it
    # satisfies the floor BY CONSTRUCTION -- handing it a lower floor returns 100% and
    # measures nothing. The specification's procedure (section 4.4) draws
    # (x*, n, delta, w) independently and only then tests section 4.6's criterion.
    # That independence is what makes v6 a rejection sampler.
    n_big = 20_000
    print(f"  v6 spec: independent draws, then test min_i w_i*delta_i >= 0.045."
          f"  {n_big:,} draws:")
    for dim in (6, 8):
        rng = np.random.default_rng(20260807 + dim)
        ok = 0
        for _ in range(n_big):
            xstar = rng.uniform(0.25, 0.55, dim)
            n_hill = rng.uniform(1.0, 3.0, dim)
            delta = rng.uniform(0.55, 0.90, dim) * np.asarray(delta_max(xstar, n_hill))
            w = rng.uniform(0.75, 1.25, dim)
            w /= w.sum()
            ok += float((w * delta).min()) >= 0.045
        rate = ok / n_big
        per = f"{1 / rate:.0f}" if rate else f">{n_big}"
        print(f"    d={dim}: {ok:>6}/{n_big}  = {rate:>7.3%}   {per:>7} draws per instance")

    # SHIPPED_CONFIG, not SamplerConfig(): the bare default carries accept_floor
    # 0.045 (the v6 value), so an earlier version of this script measured the "v8
    # shipped" rate at a floor 2.4x easier than the one the ensemble was built at
    # and reported 100% on that basis.
    v8 = SHIPPED_CONFIG
    n_small = 40
    print(f"\n  v8 SHIPPED_CONFIG (4 active, numerically computed depth, floor 0.1083), "
          f"{n_small} seeds per dim:")
    for dim in (6, 8):
        ok = 0
        for seed in range(n_small):
            inst = propose_instance(dim, seed, v8)
            if inst is None:
                continue
            good, _ = accept_instance(inst, v8)
            ok += bool(good)
        rate = ok / n_small
        se = np.sqrt(max(rate * (1 - rate), 1e-12) / n_small)
        print(f"    d={dim}: {ok:>6}/{n_small}     = {rate:>7.1%}  "
              f"(+/- {1.96 * se:.1%} at 95%)")


def q4_delta_max_distribution() -> None:
    print(f"\n{'=' * 84}\nPF2.4 · achieved delta_max, and the depth actually realised\n{'=' * 84}")
    dm = []
    for _ in range(20_000):
        xs, n = RNG.uniform(0.25, 0.55), RNG.uniform(1.0, 3.0)
        dm.append(float(delta_max(xs, n)))
    dm = np.array(dm)
    qs = [0, 5, 25, 50, 75, 95, 100]
    print("  delta_max over the nominal (x*, n) draw:")
    print("    " + "  ".join(f"p{q}={np.percentile(dm, q):.4f}" for q in qs))

    print("\n  realised depth on the shipped ensemble (numerically computed, not the formula):")
    for dim in (6, 8):
        ens = load_ensemble(dim=dim)
        td = np.array([i.true_depth for i in ens], dtype=float)
        fd = np.array([i.formula_depth for i in ens], dtype=float)
        ratio = np.median(fd / td)
        print(f"    d={dim}: true depth median {np.median(td):.4f}  min {td.min():.4f}  "
              f"max {td.max():.4f}")
        print(f"           formula/true median ratio {ratio:.3f}  "
              f"-> the formula over-states depth by {100 * (ratio - 1):.1f}%")
        print(f"           influence ratio (active/inert weight) median "
              f"{np.median([i.influence_ratio for i in ens]):.2f}x  "
              f"(1.0x means ARD has nothing to find)")
        need = 3 * 0.25 / np.sqrt(48)
        print(f"           clears the sigma_rel=0.25 threshold of {need:.4f}: "
              f"{np.mean(td >= need):.0%} of instances")


if __name__ == "__main__":
    q1_verification_case()
    q2_closed_form_on_a_beta_zero_variant()
    q3_acceptance_rate()
    q4_delta_max_distribution()
