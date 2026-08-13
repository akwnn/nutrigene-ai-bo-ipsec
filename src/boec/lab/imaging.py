"""Microscopy: acquisition provenance, focus QC, and phase-contrast coverage.

121 images carry pixels (114 Leica JPEG + 7 EVOS JPG); 114 Leica ``.metadata`` sidecars
carry the acquisition settings as JSON. The sidecars are what make a coverage number
defensible rather than decorative: a confluence comparison across images shot at
different exposure or objective measures the microscope, not the cells.
:func:`comparability_key` is therefore checked *before* any cross-image claim, and the
FN/VTN series passes -- all 18 were shot ``PH``/4X/19000/gain 1/light 45.

**Coverage is not CD31.** These are unstained phase-contrast frames. The number here is
the fraction of the field carrying cell-like texture, stamped
``coverage_frac_phase`` / ``fraction_of_field`` / ``leica-ph-4x-v1``. It is a *separate
campaign* from the flow CD31% and must never become a second column beside it
(requirement 7).

Method: phase contrast makes cells textured and bare substrate smooth, so the signal is
local variance rather than intensity. Sobel gradient magnitude -> Gaussian smoothing ->
Otsu -> small-object removal and hole filling. Otsu assumes the field is bimodal; a
frame that is entirely confluent or entirely empty has no valid split, so
:attr:`ImageFeatures.otsu_separability` travels with the number and a low value means
the threshold was drawn through noise.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from skimage import color, filters, io, morphology, transform

#: Long edge the analysis runs at. Full frames are 3072x2048; coverage is a
#: field-fraction and is stable under downsampling, which buys ~15x on 121 images.
ANALYSIS_LONG_EDGE = 1024
#: Blobs of this many downsampled pixels or fewer are debris, not cells. Expressed as
#: a max because scikit-image 0.26 deprecated ``min_size``/``area_threshold`` in favour
#: of ``max_size``, whose comparison is "smaller than *or equal to*".
MAX_DEBRIS_PX = 63

METRIC_NAME = "coverage_frac_phase"
METRIC_UNIT = "fraction_of_field"
METRIC_PROTOCOL = "leica-ph-4x-v1"


@dataclass(frozen=True)
class AcquisitionMeta:
    """A Leica ``.metadata`` sidecar."""

    contrast: str | None
    objective: str | None
    exposure: int | None
    gain: float | None
    light_intensity: float | None
    width: int | None
    height: int | None
    created: datetime | None
    raw: dict

    @property
    def comparability_key(self) -> tuple:
        """Images sharing this key were shot under settings that can be compared."""
        return (self.contrast, self.objective, self.exposure, self.gain, self.light_intensity)


def read_sidecar(path: Path) -> AcquisitionMeta:
    """Parse ``<image>.jpeg.metadata``."""
    d = json.loads(Path(path).read_text(encoding="utf-8", errors="replace"))
    created = None
    raw_created = d.get("createdTime")
    if raw_created:
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                created = datetime.strptime(raw_created, fmt)
                break
            except ValueError:
                continue
    return AcquisitionMeta(
        contrast=d.get("contrast"),
        objective=d.get("objective"),
        exposure=d.get("exposure"),
        gain=d.get("gain"),
        light_intensity=d.get("lightIntensity"),
        width=d.get("width"),
        height=d.get("height"),
        created=created,
        raw=d,
    )


def sidecar_for(image_path: Path) -> Path | None:
    """Leica pairs ``x.jpeg`` with ``x.jpeg.metadata``. EVOS files have no sidecar."""
    cand = Path(str(image_path) + ".metadata")
    return cand if cand.exists() else None


def load_gray(path: Path, long_edge: int = ANALYSIS_LONG_EDGE) -> np.ndarray:
    """Greyscale float image in [0, 1], downsampled so the long edge is ``long_edge``."""
    img = io.imread(str(path))
    if img.ndim == 3:
        img = color.rgb2gray(img[..., :3])
    else:
        img = img.astype(float)
        if img.max() > 1.0:
            img = img / 255.0
    scale = long_edge / max(img.shape)
    if scale < 1.0:
        img = transform.rescale(img, scale, anti_aliasing=True)
    return img


def focus_score(gray: np.ndarray) -> float:
    """Variance of the Laplacian. Higher is sharper.

    Scale-dependent, so it ranks images within a comparability group and means nothing
    across groups.
    """
    return float(filters.laplace(gray).var())


@dataclass(frozen=True)
class ImageFeatures:
    """Per-image QC and coverage."""

    path: str
    width: int
    height: int
    mean_intensity: float
    std_intensity: float
    focus: float
    coverage: float
    otsu_threshold: float
    otsu_separability: float
    comparability_key: tuple | None = None

    @property
    def coverage_is_trustworthy(self) -> bool:
        """Otsu needs a bimodal field. Low separability means the split is noise."""
        return self.otsu_separability >= 0.05


def _otsu_separability(values: np.ndarray, threshold: float) -> float:
    """Between-class variance over total variance at ``threshold`` -- Otsu's own
    objective, normalised. 0 means the two classes are indistinguishable."""
    total = values.var()
    if total <= 0:
        return 0.0
    lo, hi = values[values <= threshold], values[values > threshold]
    if lo.size == 0 or hi.size == 0:
        return 0.0
    w0, w1 = lo.size / values.size, hi.size / values.size
    return float((w0 * w1 * (lo.mean() - hi.mean()) ** 2) / total)


def texture_coverage(gray: np.ndarray) -> tuple[float, float, float]:
    """``(coverage_fraction, otsu_threshold, separability)``.

    Cells scatter light and produce edges; bare substrate is flat. The response is the
    Sobel gradient magnitude, smoothed so a cell body counts as one object rather than
    an outline.
    """
    edges = filters.sobel(gray)
    response = filters.gaussian(edges, sigma=2.0)
    thr = float(filters.threshold_otsu(response))
    sep = _otsu_separability(response.ravel(), thr)
    mask = response > thr
    mask = morphology.remove_small_objects(mask, max_size=MAX_DEBRIS_PX)
    mask = morphology.remove_small_holes(mask, max_size=MAX_DEBRIS_PX)
    return float(mask.mean()), thr, sep


def analyse_image(path: Path, *, long_edge: int = ANALYSIS_LONG_EDGE) -> ImageFeatures:
    """Full per-image feature extraction."""
    path = Path(path)
    gray = load_gray(path, long_edge=long_edge)
    coverage, thr, sep = texture_coverage(gray)
    side = sidecar_for(path)
    meta = read_sidecar(side) if side else None
    return ImageFeatures(
        path=path.name,
        width=gray.shape[1],
        height=gray.shape[0],
        mean_intensity=float(gray.mean()),
        std_intensity=float(gray.std()),
        focus=focus_score(gray),
        coverage=coverage,
        otsu_threshold=thr,
        otsu_separability=sep,
        comparability_key=meta.comparability_key if meta else None,
    )


def comparability_groups(metas: dict[str, AcquisitionMeta]) -> dict[tuple, list[str]]:
    """Bucket image names by acquisition settings."""
    groups: dict[tuple, list[str]] = {}
    for name, meta in metas.items():
        groups.setdefault(meta.comparability_key, []).append(name)
    return {k: sorted(v) for k, v in groups.items()}
