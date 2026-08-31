# Historical DC results: constant reconstructed variance

These five files are Joseph's original DC outputs. Their numerical bytes are unchanged from
the files committed at `843a44f` and propagated at `549a451`.

The DoE certification path used one constant reconstructed `Yvar` based on the mean absolute
response instead of the per-well observation variances returned by the evaluator. That is not
the registered oracle variance model, which includes response-dependent relative variance and
additive variance per well. The files are retained for auditability and reproduction of the
historical analysis, not for confirmatory inference.

Git history also shows that `scripts/analyse_dc_doe_certificate.py` was committed after partial
DC result files already existed. The acceptance rule appeared in the earlier specification,
but the claim that the analyser itself was frozen before data landed is unsupported.

Original SHA-256 digests:

| file | SHA-256 |
|---|---|
| `dc-ackley.json` | `70860f8d668bcfc1ccef8166c29ab8d2d67ee17990a96d58602d5efe8815502e` |
| `dc-hartmann6.json` | `5ec0fa12b74d269694cc08c5548213079ef37d2fb4d0ed6e148a0940a17d28c3` |
| `dc-hill.json` | `d61c69aff26590fab9f54f2b880cc6cbecebe53e040b296b178b5cf3af19bda6` |
| `dc-levy.json` | `408b633fc13feb3e6b5126043e894774c444b702422a0be4a0797a10d800592b` |
| `dc-rosenbrock.json` | `db511648fed6b9e850c8e470697afde1800416c1fe3d2087f9b167a8ca798339` |
