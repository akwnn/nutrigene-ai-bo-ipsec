"""FCS reading for the CytoFLEX LX drop.

Parsing is delegated to ``flowio`` and the transforms to ``flowutils`` -- the two
packages FlowKit itself is built on. Rolling our own logicle was the alternative and
is the easier thing to get quietly wrong: a mis-parameterised biexponential moves
every gate, and the failure mode is a plausible CD31 percentage rather than a crash.

Instrument facts established by reading all 52 files, not from the notebook:

* ``$CYT = CytoFLEX LX``, ``$CYTSN = BG17015``, CytExpert. **Not a NovoCyte** -- the
  README, BO-PURPOSE.md and the ``novocyte-...`` metric string were wrong.
* 38 parameters, ``$PnR = 16777216`` (2^24). The logicle ``t`` must be that, not
  flowutils' 262144 default, or the top two decades of every stained sample fold.
* ``$SPILLOVER`` is exactly the 32x32 identity and ``USCOMP = False``: **no
  compensation was applied at acquisition.** For a two-colour panel that inflates
  double-positives, and it is why B610-A trails B525-A in :mod:`boec.lab.gating`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path

import numpy as np

import flowio
from flowutils import transforms

#: ``$PnR`` on every channel of this instrument. Logicle's upper asymptote.
LOGICLE_T = 16_777_216.0
#: Decades displayed. 4.5 is the flowutils/FlowJo convention and is kept.
LOGICLE_M = 4.5
#: Width of the linearised region around zero. 0.5 handles the ~12% negative events
#: that B525-A carries; see the ``neg%`` column in the acquisition report.
LOGICLE_W = 0.5

_FCS_DATE_FORMATS = ("%d-%b-%Y", "%d-%b-%y", "%Y-%m-%d")


@dataclass(frozen=True)
class FcsSummary:
    """Everything readable from the header and TEXT segment, without touching events.

    Cheap enough to run over all 52 files for the provenance index.
    """

    path: str
    cytometer: str
    serial: str
    software_fil: str
    acquired_date: date | None
    acquired_time: time | None
    events: int
    parameters: int
    detectors: tuple[str, ...]
    fcs_version: str
    spillover_is_identity: bool | None
    spillover_n: int
    operator: str

    @property
    def aborted(self) -> bool:
        """Zero events. The eight ``Exp_20260806_2`` tubes are the whole population."""
        return self.events == 0

    @property
    def fluorescence_detectors(self) -> tuple[str, ...]:
        """Area channels only, scatter and Time excluded -- the gateable signals."""
        return tuple(
            d for d in self.detectors if d.endswith("-A") and not d.startswith(("FSC", "SSC"))
        )


def _parse_fcs_date(raw: str | None) -> date | None:
    if not raw:
        return None
    for fmt in _FCS_DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _parse_fcs_time(raw: str | None) -> time | None:
    if not raw:
        return None
    txt = raw.strip().split(".")[0]
    try:
        return datetime.strptime(txt, "%H:%M:%S").time()
    except ValueError:
        return None


def parse_spillover(text: dict[str, str]) -> tuple[np.ndarray, list[str]] | None:
    """``$SPILLOVER`` -> ``(matrix (n, n), labels)``.

    Returns ``None`` when the keyword is absent. The stored form is
    ``n,label_1,...,label_n,m_11,m_12,...`` in row-major order.
    """
    raw = text.get("spillover") or text.get("$spillover")
    if not raw:
        return None
    parts = raw.split(",")
    n = int(parts[0])
    labels = parts[1 : 1 + n]
    values = np.array([float(x) for x in parts[1 + n : 1 + n + n * n]], dtype=float)
    if values.size != n * n:
        return None
    return values.reshape(n, n), labels


def read_summary(path: Path) -> FcsSummary:
    """Header + TEXT only. Does not decode the DATA segment."""
    path = Path(path)
    # only_text skips the DATA segment: 75 MB of events stay on disk for a keyword read.
    fd = flowio.FlowData(str(path), ignore_offset_error=True, only_text=True)
    text = fd.text
    spill = parse_spillover(text)
    return FcsSummary(
        path=path.name,
        cytometer=text.get("cyt", "unknown"),
        serial=text.get("cytsn", ""),
        software_fil=text.get("sys", ""),
        acquired_date=_parse_fcs_date(text.get("date")),
        acquired_time=_parse_fcs_time(text.get("btim")),
        events=int(fd.event_count),
        parameters=int(fd.channel_count),
        detectors=tuple(fd.pns_labels),
        fcs_version=str(fd.version),
        spillover_is_identity=(
            bool(np.allclose(spill[0], np.eye(len(spill[1])))) if spill else None
        ),
        spillover_n=len(spill[1]) if spill else 0,
        operator=text.get("op", ""),
    )


def read_events(path: Path) -> tuple[np.ndarray, list[str]]:
    """``(n_events, n_params)`` float array plus the ``$PnS`` detector labels.

    Raises:
        ValueError: on a zero-event file. Returning an empty array would let a caller
            average over nothing and report 0.0% rather than noticing the abort.
    """
    fd = flowio.FlowData(str(path), ignore_offset_error=True)
    if fd.event_count == 0:
        raise ValueError(
            f"{Path(path).name} has 0 events -- aborted acquisition, not a measurement"
        )
    return fd.as_array(), list(fd.pns_labels)


def detector_index(labels: list[str], detector: str) -> int:
    """Column of ``detector`` (e.g. ``'B525-A'``) in the event array."""
    try:
        return labels.index(detector)
    except ValueError as exc:
        raise KeyError(f"{detector!r} not among {labels}") from exc


def logicle(events: np.ndarray, indices: list[int]) -> np.ndarray:
    """Logicle-transform the given columns in place on a copy.

    ``t`` is this instrument's ``$PnR``, not the flowutils default. See module docstring.
    """
    return transforms.logicle(
        np.asarray(events, dtype=float),
        indices,
        t=LOGICLE_T,
        m=LOGICLE_M,
        w=LOGICLE_W,
    )
