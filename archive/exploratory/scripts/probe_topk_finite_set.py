"""EXPLORATORY feasibility probe: does the finite-set estimand fix abstention?
Not a registered result. Small n, versionb arm only."""
import sys, importlib.util, warnings, json, torch, time
warnings.filterwarnings("ignore"); torch.set_num_threads(1)
sys.path.insert(0, "src")

def _mod(name, fn):
    s = importlib.util.spec_from_file_location(name, "scripts/" + fn)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

KV = _mod("kv", "run_kv_plate2_certificate.py")
from boec.designspace import tau_quantile
from boec.norms import sobol_grid
from boec.replay import unit_bounds
from boec.surrogate import build_gp
from boec.topk import topk_columns

P = KV.p8(); p2 = P.p2()
FAMS = ["ackley", "hartmann6", "levy", "rosenbrock"]
SEEDS = range(int(sys.argv[1]) if len(sys.argv) > 1 else 8)
CS = (1.0, 1.5, 2.0)
grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)

tau_by = {}
for f in FAMS:
    with torch.no_grad():
        t = P.evaluator_for(f, f, 0).truth(grid).reshape(-1).double()
    tau_by[f] = {p: float(tau_quantile(t, p)) for p in (0.30, 0.10)}

rows = []
t0 = time.time()
for f in FAMS:
    for s in SEEDS:
        ev = P.evaluator_for(f, f, s)
        X, Y, Yvar, _ = KV.build(f, "versionb", s)
        with torch.no_grad():
            truth_sub = ev.truth(X_sub).reshape(-1).double()
        m = build_gp(X, Y, Yvar, unit_bounds(P.DIM))   # fitting needs grad
        with torch.no_grad():
            post = m.posterior(X_sub)
            mean = post.mean.reshape(-1, 1).double()
            cov = post.mvn.covariance_matrix.double()
            cov = cov + 1e-8 * torch.eye(cov.shape[0], dtype=torch.double)
            L = torch.linalg.cholesky(cov)
            g = torch.Generator().manual_seed(s)
            z = torch.randn(cov.shape[0], P.N_DRAWS, generator=g, dtype=torch.double)
        for c in CS:
            with torch.no_grad():
                draws = (mean + (c * L) @ z).T
                for p, tau in tau_by[f].items():
                    r = {"family": f, "seed": s, "c": c, "p": p}
                    r.update(p2.vorobev_columns(draws, truth_sub, tau, p2.ALPHAS))
                    r.update(topk_columns(draws, truth_sub, tau, alphas=(0.95,)))
                    rows.append(r)
            del draws
        del m
    print(f"  {f} done ({time.time()-t0:.0f}s)", flush=True)
json.dump(rows, open("results/probe-topk-finite-set.json", "w"))
print("rows", len(rows))
