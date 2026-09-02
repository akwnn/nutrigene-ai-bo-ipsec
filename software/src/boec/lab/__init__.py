"""In-house wet-lab ingestion for ``research/data/lab``.

Phase 1 is a synthetic oracle and Phase 2 replays digitized published figures. This
subpackage is the first code that touches instrument output from the Nutrigene bench.

The governing rule is :doc:`research/data/lab/overlay/BO-PURPOSE.md`: **the optimizer only eats
``(x, y)`` rows** -- coded factor levels plus one locked metric. Of the 300 files
under ``raw/``, 12 can become optimizer input. That does not make the other 288 waste: they
are provenance, gating references, comparability controls, and QC. This package
reads every one of them, and is careful about which of them are allowed to become a
number the optimizer sees.

Two rules are enforced in code rather than in a README:

1. **No metric mixing.** CD31% by flow and phase-contrast coverage are different
   numbers with different :class:`~boec.space.MetricIdentity` stamps and separate
   campaigns. Requirement 7.
2. **No invented outcomes.** Anything derived by software lands in ``research/data/lab/derived/``
   marked ``candidate`` and carries the evidence that produced it. Promotion to a
   campaign CSV is a human act. See :mod:`boec.lab.gating`.
"""

from __future__ import annotations

from .evaluator import (
    GatingIncompleteError,
    MetricMismatchError,
    load_lab_evaluator,
)
from .manifest import (
    LabFile,
    Modality,
    build_file_index,
    load_roles,
    verify_checksums,
    walk_lab,
)

__all__ = [
    "GatingIncompleteError",
    "LabFile",
    "MetricMismatchError",
    "Modality",
    "build_file_index",
    "load_lab_evaluator",
    "load_roles",
    "verify_checksums",
    "walk_lab",
]
