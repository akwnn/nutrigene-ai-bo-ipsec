"""Calibrate c on the REAL iPSC-EC assay by leave-one-out. No new experiments needed.

The open item was 'c is uncalibrated for this assay'. Calibrating it does NOT require
replicates: each of the 12 tubes can be held out, predicted from the other 11, and the
standardised residual computed. If the posterior is honest those residuals are N(0,1);
the inflation that makes them so IS c for this assay.

Two GP variants are compared, because the mean-marginalisation fix should change the
answer: a collapsed posterior needs enormous c, an honest one should need c near 1.
"""
import sys, warnings, torch, numpy as np, importlib.util
warnings.filterwarnings("ignore"); torch.set_num_threads(1); sys.path.insert(0, "src")
spec = importlib.util.spec_from_file_location("r", "software/scripts/run_real_ipsc_certification.py")
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
from boec.surrogate import build_gp
from boec.meanmarg import mean_marginalised_covariance
from boec.selfcalib import calibration_inflation

X, Y, Yvar = R.load()
n = X.shape[0]
b = torch.tensor([[0., 0.], [1., 1.]], dtype=torch.double)

for label in ("raw", "meanmarg"):
    mus, sds, ys = [], [], []
    for i in range(n):
        keep = [j for j in range(n) if j != i]
        m = build_gp(X[keep], Y[keep], Yvar[keep], b)
        xi = X[i:i+1]
        with torch.no_grad():
            p = m.posterior(xi)
            mu = float(p.mean.reshape(-1)[0])
            var = float(p.variance.reshape(-1)[0])
        if label == "meanmarg":
            var = float(mean_marginalised_covariance(m, xi).reshape(-1)[0])
        # predictive variance for an OBSERVATION adds the tube's own measurement noise
        sd = (var + float(Yvar[i])) ** 0.5
        mus.append(mu); sds.append(sd); ys.append(float(Y[i]))
    mus, sds, ys = np.array(mus), np.array(sds), np.array(ys)
    z = (ys - mus) / sds
    c = calibration_inflation(ys, mus, sds)
    cov68 = float(np.mean(np.abs(z) <= 1.0)); cov95 = float(np.mean(np.abs(z) <= 1.96))
    print(f"--- {label} ---")
    print(f"  LOO residual z: mean {z.mean():+.3f}  sd {z.std(ddof=1):.3f}  max|z| {np.abs(z).max():.2f}")
    print(f"  coverage: 68% nominal -> {cov68:.3f}   95% nominal -> {cov95:.3f}")
    print(f"  calibration_inflation c = {c:.3f}")
    print(f"  mean posterior sd (excl. noise): "
          f"{np.mean(np.sqrt(np.maximum(sds**2 - float(Yvar.mean()),0))):.3f}")
