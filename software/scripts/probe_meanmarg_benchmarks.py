"""EXPLORATORY: does mean-marginalisation change the benchmark certificate?
Compares raw vs mean-marginalised covariance at c=1.0 and c=1.5. Not registered."""
import sys, importlib.util, warnings, json, torch, time
warnings.filterwarnings("ignore"); torch.set_num_threads(1)
sys.path.insert(0, "src")

def _mod(n, f):
    s = importlib.util.spec_from_file_location(n, "software/scripts/" + f)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

KV = _mod("kv", "run_kv_plate2_certificate.py")
from boec.designspace import tau_quantile
from boec.norms import sobol_grid
from boec.replay import unit_bounds
from boec.surrogate import build_gp
from boec.meanmarg import mean_marginalised_covariance

P = KV.p8(); p2 = P.p2()
FAMS = ["ackley", "hartmann6", "levy", "rosenbrock"]
SEEDS = range(int(sys.argv[1]) if len(sys.argv) > 1 else 6)
grid = sobol_grid(P.DIM, p2.GRID_N, seed=p2.GRID_SEED)
X_sub = sobol_grid(P.DIM, p2.SUBSET_N, seed=p2.GRID_SEED)
tau_by = {}
for f in FAMS:
    with torch.no_grad():
        t = P.evaluator_for(f, f, 0).truth(grid).reshape(-1).double()
    tau_by[f] = {p: float(tau_quantile(t, p)) for p in (0.30, 0.10)}

rows = []; t0 = time.time()
for f in FAMS:
    for s in SEEDS:
        ev = P.evaluator_for(f, f, s)
        X, Y, Yvar, _ = KV.build(f, "versionb", s)
        with torch.no_grad():
            truth_sub = ev.truth(X_sub).reshape(-1).double()
        m = build_gp(X, Y, Yvar, unit_bounds(P.DIM))
        with torch.no_grad():
            post = m.posterior(X_sub)
            mean = post.mean.reshape(-1, 1).double()
            raw = post.mvn.covariance_matrix.double()
        mm = mean_marginalised_covariance(m, X_sub)
        sd_raw = float(raw.diagonal().sqrt().mean())
        sd_mm = float(mm.diagonal().sqrt().mean())
        I = torch.eye(raw.shape[0], dtype=torch.double)
        gen = torch.Generator().manual_seed(s)
        z = torch.randn(raw.shape[0], P.N_DRAWS, generator=gen, dtype=torch.double)
        for label, C in (("raw", raw), ("meanmarg", mm)):
            L = torch.linalg.cholesky(C + 1e-8 * I)
            for c in (1.0, 1.5):
                with torch.no_grad():
                    draws = (mean + c * L @ z).T
                    for p, tau in tau_by[f].items():
                        r = {"family": f, "seed": s, "cov": label, "c": c, "p": p,
                             "sd_raw": sd_raw, "sd_mm": sd_mm}
                        r.update(p2.vorobev_columns(draws, truth_sub, tau, p2.ALPHAS))
                        rows.append(r)
                del draws
        del m
    print(f"  {f} done ({time.time()-t0:.0f}s)", flush=True)
json.dump(rows, open("research/results/probe-meanmarg-benchmarks.json","w"))
print("rows", len(rows))
