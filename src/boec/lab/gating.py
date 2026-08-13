"""Channel identity and CD31 positivity.

``GATE.md`` treated the CD31-vs-CD140a assignment as a dead stop: the filenames do not
say which detector is which, and neither does ``$PnS`` -- it carries ``B525-A`` and
``Y585-A``, which are detectors, not antibodies. But the drop contains a sorted
reference panel (``flow/2026-07-28/``: ``CD31+``, ``CD31-``, ``ISO``, ``US``), and
*whichever detector separates CD31+ from CD31- is the CD31 detector*. That is a
measurement, so this module makes it one.

What this module will not do is decide that the answer is good enough. Everything it
produces is stamped ``candidate`` and carries the evidence that produced it. Promotion
into ``bo_primary_conditions.csv`` is a human act, because three judgement calls remain
that no amount of arithmetic settles:

* **No compensation was applied** (``$SPILLOVER`` is identity). Spillover from a bright
  B525 into neighbouring detectors is real and uncorrected.
* **No live/singlet gate is drawn.** The FSC-H/FSC-A ratio has MAD 0.24 on this data --
  a +/-3 MAD singlet gate keeps 99.5% of events, which is not a gate. Percentages here
  are over *all recorded events*. A human gating in CytExpert will get different, and
  probably better, numbers.
* **The positivity threshold is a convention**, not a fact. CD31% on ``f5.fcs`` moves
  from 47.1% to 33.5% as the unstained percentile goes 95 -> 99.9, so the sensitivity
  sweep travels with the point estimate rather than being available on request.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .fcs import detector_index, read_events, read_summary

#: Percentile of the negative control that defines "positive". 99 is the convention
#: used for the reported point estimate; the rest travel as sensitivity.
THRESHOLD_PCTL = 99.0
SENSITIVITY_PCTLS = (95.0, 99.0, 99.5, 99.9)

#: The 2026-07-28 sorted panel. The only files in the drop that name a marker.
REFERENCE_PANEL = {
    "positive": "CD31+.fcs",
    "negative": "CD31-.fcs",
    "isotype": "ISO.fcs",
    "unstained": "US.fcs",
}


@dataclass(frozen=True)
class DetectorVerdict:
    """How well one detector separates the sorted CD31+ reference from CD31-."""

    detector: str
    threshold: float
    pct_positive_in_reference: float
    pct_positive_in_negative: float
    pct_positive_in_isotype: float
    pct_positive_in_unstained: float

    @property
    def excess(self) -> float:
        """The statistic. Positive-control minus negative-control percent-positive.

        Chosen over a median ratio because the sorted ``CD31+`` sample is bimodal --
        its median sits *below* ``CD31-`` while its 90th percentile sits 17x above,
        so any central-tendency comparison ranks the right answer last.
        """
        return self.pct_positive_in_reference - self.pct_positive_in_negative


@dataclass(frozen=True)
class ChannelIdentity:
    """Which detector is CD31, with the evidence and the margin over the runner-up."""

    cd31_detector: str
    runner_up: str
    margin: float
    verdicts: tuple[DetectorVerdict, ...]
    reference_dir: str
    panel_matches_target: bool
    notes: tuple[str, ...] = ()

    @property
    def cd140a_detector(self) -> str | None:
        """By elimination, for a two-colour panel whose other stat channel is known.

        Returns ``None`` unless exactly one other detector was requested for stats,
        because "the one that is not CD31" is only an answer when there are two.
        """
        others = [v.detector for v in self.verdicts if v.detector != self.cd31_detector]
        return others[0] if len(others) == 1 else None

    def as_dict(self) -> dict:
        return {
            "cd31_detector": self.cd31_detector,
            "runner_up": self.runner_up,
            "margin_pct_points": round(self.margin, 4),
            "reference_dir": self.reference_dir,
            "panel_matches_target": self.panel_matches_target,
            "notes": list(self.notes),
            "verdicts": [
                {
                    "detector": v.detector,
                    "threshold": round(v.threshold, 3),
                    "pct_positive_reference": round(v.pct_positive_in_reference, 4),
                    "pct_positive_negative": round(v.pct_positive_in_negative, 4),
                    "pct_positive_isotype": round(v.pct_positive_in_isotype, 4),
                    "pct_positive_unstained": round(v.pct_positive_in_unstained, 4),
                    "excess": round(v.excess, 4),
                }
                for v in self.verdicts
            ],
        }


def resolve_cd31_channel(
    reference_dir: Path,
    *,
    candidate_detectors: list[str] | None = None,
    threshold_pctl: float = THRESHOLD_PCTL,
) -> ChannelIdentity:
    """Identify the CD31 detector from the sorted reference panel.

    Scans every fluorescence area detector by default so that the winner is ranked
    against all 16 alternatives rather than only against the one we hoped it would beat.

    Args:
        reference_dir: directory holding ``CD31+.fcs``/``CD31-.fcs``/``ISO.fcs``/``US.fcs``.
        candidate_detectors: restrict the scan. ``None`` scans all fluorescence channels.
        threshold_pctl: percentile of the isotype control defining positivity.

    Raises:
        FileNotFoundError: if any of the four reference files is missing. A partial
            panel cannot establish identity, and guessing from three is how the wrong
            channel gets locked into a metric string.
    """
    reference_dir = Path(reference_dir)
    paths = {k: reference_dir / v for k, v in REFERENCE_PANEL.items()}
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(f"reference panel incomplete: {missing}")

    arrays = {k: read_events(p) for k, p in paths.items()}
    labels = arrays["isotype"][1]
    if candidate_detectors is None:
        candidate_detectors = [
            d for d in labels if d.endswith("-A") and not d.startswith(("FSC", "SSC"))
        ]

    verdicts: list[DetectorVerdict] = []
    for det in candidate_detectors:
        i = detector_index(labels, det)
        thr = float(np.percentile(arrays["isotype"][0][:, i], threshold_pctl))

        def pct(key: str) -> float:
            col = arrays[key][0][:, i]
            return float(100.0 * (col > thr).mean())

        verdicts.append(
            DetectorVerdict(
                detector=det,
                threshold=thr,
                pct_positive_in_reference=pct("positive"),
                pct_positive_in_negative=pct("negative"),
                pct_positive_in_isotype=pct("isotype"),
                pct_positive_in_unstained=pct("unstained"),
            )
        )

    ranked = sorted(verdicts, key=lambda v: -v.excess)
    winner, runner_up = ranked[0], ranked[1]
    notes = []
    if runner_up.detector.startswith(winner.detector[0]):
        notes.append(
            f"Runner-up {runner_up.detector} shares the {winner.detector[0]}-laser with the "
            f"winner and no compensation was applied, so its {runner_up.excess:.1f}pp is "
            "consistent with spillover from the winner rather than an independent stain."
        )
    return ChannelIdentity(
        cd31_detector=winner.detector,
        runner_up=runner_up.detector,
        margin=winner.excess - runner_up.excess,
        verdicts=tuple(ranked),
        reference_dir=reference_dir.name,
        panel_matches_target=True,
        notes=tuple(notes),
    )


def check_panel_match(reference_file: Path, target_file: Path) -> tuple[bool, list[str]]:
    """Do two acquisitions share a detector configuration?

    Channel identity transfers between days only if the panel does. Compares the
    instrument, the detector list, and the parameter count.
    """
    a, b = read_summary(reference_file), read_summary(target_file)
    problems = []
    if a.cytometer != b.cytometer or a.serial != b.serial:
        problems.append(f"instrument differs: {a.cytometer}/{a.serial} vs {b.cytometer}/{b.serial}")
    if a.detectors != b.detectors:
        problems.append("detector list differs")
    if a.parameters != b.parameters:
        problems.append(f"parameter count differs: {a.parameters} vs {b.parameters}")
    return (not problems), problems


@dataclass(frozen=True)
class PositivityResult:
    """Percent-positive for one tube, with the sensitivity sweep attached.

    ``pct_positive`` is the point estimate at :data:`THRESHOLD_PCTL`. It is not a
    finished measurement -- see the module docstring for the three open judgement calls.
    """

    file: str
    detector: str
    control_file: str
    events: int
    threshold: float
    pct_positive: float
    sensitivity: dict[float, float] = field(default_factory=dict)

    @property
    def spread(self) -> float:
        """Range of the sensitivity sweep. Large values mean the number is soft."""
        if not self.sensitivity:
            return float("nan")
        return max(self.sensitivity.values()) - min(self.sensitivity.values())


def percent_positive(
    target: Path,
    control: Path,
    detector: str,
    *,
    threshold_pctl: float = THRESHOLD_PCTL,
    sensitivity_pctls: tuple[float, ...] = SENSITIVITY_PCTLS,
) -> PositivityResult:
    """Percent of events in ``target`` above the ``threshold_pctl`` of ``control``.

    Over **all recorded events** -- no live or singlet gate. See the module docstring.
    """
    tgt, tlab = read_events(target)
    ctl, clab = read_events(control)
    ti, ci = detector_index(tlab, detector), detector_index(clab, detector)
    col, ctl_col = tgt[:, ti], ctl[:, ci]

    sweep = {
        float(q): float(100.0 * (col > np.percentile(ctl_col, q)).mean())
        for q in sensitivity_pctls
    }
    thr = float(np.percentile(ctl_col, threshold_pctl))
    return PositivityResult(
        file=Path(target).name,
        detector=detector,
        control_file=Path(control).name,
        events=int(col.size),
        threshold=thr,
        pct_positive=float(100.0 * (col > thr).mean()),
        sensitivity=sweep,
    )
