"""The plate-reader endpoint, read rather than dismissed.

``BO-PURPOSE.md`` files this one file under "wrong metric" -- absorbance at 562 nm with
no condition labels -- and stops. Both halves of that are true, and reading it turns
both from assumptions into verified facts, plus one identification the note missed.

What the workbook actually contains: a Thermo Multiskan SkyHigh endpoint, 96-well,
2026-06-22, single wavelength 562 nm. **562 nm is the BCA readout**, and rows A and B
columns 1-6 hold a monotonic duplicate series that fits a straight line -- a BCA
standard curve. So the plate is total-protein quantification, not a CD31 measurement.
That is a stronger statement than "wrong metric": it says *which* assay it is, which is
what lets a future campaign know it will never be a CD31 outcome no matter what labels
turn up.

The "Plate layout" sheet is present and every one of its 96 cells is ``X``. The missing
condition map is therefore a fact about the file, not an inference from the filename.

xlsx is a zip of XML, so this uses ``zipfile`` + ``xml.etree`` exactly as
:mod:`boec.lab.protocol` does for docx. openpyxl is not installed and is not needed.
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_CELL_REF = re.compile(r"([A-Z]+)(\d+)")

#: 562 nm is the bicinchoninic-acid assay readout.
BCA_WAVELENGTH_NM = 562


def _shared_strings(z: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    root = ET.fromstring(z.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iter(NS + "t")) for si in root.findall(NS + "si")]


def read_workbook(path: Path) -> dict[str, dict[str, str]]:
    """``{sheet_name: {cell_ref: value}}``. Shared strings resolved, formulas ignored."""
    path = Path(path)
    z = zipfile.ZipFile(path)
    sst = _shared_strings(z)
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    names = [s.get("name") for s in wb.iter(NS + "sheet")]

    out: dict[str, dict[str, str]] = {}
    for i, name in enumerate(names, start=1):
        member = f"xl/worksheets/sheet{i}.xml"
        if member not in z.namelist():
            continue
        root = ET.fromstring(z.read(member))
        cells: dict[str, str] = {}
        for c in root.iter(NS + "c"):
            ref, ctype = c.get("r"), c.get("t")
            v = c.find(NS + "v")
            if ref is None or v is None or v.text is None:
                continue
            val = v.text
            if ctype == "s":
                val = sst[int(val)]
            cells[ref] = val
        out[str(name)] = cells
    return out


@dataclass(frozen=True)
class StandardCurve:
    """Least-squares fit of a monotonic duplicate absorbance series."""

    row_labels: tuple[str, ...]
    readings: tuple[tuple[float, ...], ...]
    slope: float
    intercept: float
    r_squared: float

    @property
    def is_monotonic_duplicate_series(self) -> bool:
        """What can actually be asserted: two rows, both strictly increasing.

        ``r_squared`` is regressed against *column index*, not concentration, because
        the layout sheet is unlabelled and the dilution scheme is therefore unknown. A
        two-fold serial dilution would be linear in log concentration and curved in
        index, so a middling R^2 here is uninformative about assay quality and must not
        be reported as one. The statistic is descriptive only.
        """
        return len(self.row_labels) >= 2 and all(
            all(b > a for a, b in zip(s, s[1:])) for s in self.readings
        )


@dataclass(frozen=True)
class PlateRead:
    """One endpoint absorbance plate."""

    path: str
    instrument: str
    serial: str
    measured_at: str
    wavelength_nm: int
    assay_type: str
    plate_template: str
    wells: dict[str, float]
    layout_labelled: bool
    standard_curve: StandardCurve | None

    @property
    def looks_like_bca(self) -> bool:
        return self.wavelength_nm == BCA_WAVELENGTH_NM and self.standard_curve is not None

    @property
    def n_wells(self) -> int:
        return len(self.wells)


def _find_value_right_of(cells: dict[str, str], label: str) -> str:
    """``General information`` stores ``label`` in column C and its value in column D."""
    for ref, val in cells.items():
        if val.strip().rstrip(":") == label.rstrip(":"):
            m = _CELL_REF.match(ref)
            if m:
                col, row = m.group(1), m.group(2)
                nxt = chr(ord(col[-1]) + 1)
                return cells.get(f"{col[:-1]}{nxt}{row}", "")
    return ""


def _fit_standard_curve(rows: dict[str, list[float]]) -> StandardCurve | None:
    """Fit the duplicate rows whose readings increase monotonically.

    Returns ``None`` if fewer than two such rows exist -- a single increasing row is a
    gradient, not a curve with replication.
    """
    monotonic = {
        label: vals
        for label, vals in rows.items()
        if len(vals) >= 4 and all(b > a for a, b in zip(vals, vals[1:]))
    }
    if len(monotonic) < 2:
        return None
    labels = tuple(sorted(monotonic))
    series = tuple(tuple(monotonic[k]) for k in labels)
    n = min(len(s) for s in series)
    x = np.tile(np.arange(n, dtype=float), len(series))
    y = np.concatenate([np.asarray(s[:n]) for s in series])
    slope, intercept = np.polyfit(x, y, 1)
    pred = slope * x + intercept
    ss_res = float(((y - pred) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return StandardCurve(
        row_labels=labels, readings=series, slope=float(slope), intercept=float(intercept),
        r_squared=float(r2),
    )


def read_plate(path: Path) -> PlateRead:
    """Parse an endpoint-absorbance workbook into structure plus a curve verdict."""
    path = Path(path)
    book = read_workbook(path)
    info = book.get("General information", {})
    raw = book.get("Raw data 562 nm", {})
    layout = book.get("Plate layout", {})

    wells: dict[str, float] = {}
    well_col = {ref: val for ref, val in raw.items() if ref.startswith("A")}
    for ref, well_name in well_col.items():
        m = _CELL_REF.match(ref)
        if not m or not re.match(r"^[A-H]\s*\d+$", str(well_name)):
            continue
        row_no = m.group(2)
        value = raw.get(f"C{row_no}")
        if value is None:
            continue
        try:
            wells[str(well_name).replace(" ", "")] = float(value)
        except ValueError:
            continue

    # Row 1 holds column numbers and column A holds row letters; the grid itself is
    # B2 onward. Counting the headers as content reports every plate as labelled.
    layout_values = set()
    for ref, v in layout.items():
        m = _CELL_REF.match(ref)
        if not m:
            continue
        col, row_no = m.group(1), int(m.group(2))
        if row_no < 2 or col == "A":
            continue
        layout_values.add(v.strip().upper())
    layout_labelled = bool(layout_values - {"X", ""})

    by_row: dict[str, list[float]] = {}
    for name, val in sorted(wells.items(), key=lambda kv: (kv[0][0], int(kv[0][1:]))):
        by_row.setdefault(name[0], []).append(val)
    # A BCA curve occupies the first columns; trailing blanks would break monotonicity.
    curve = _fit_standard_curve({k: v[:6] for k, v in by_row.items()})

    wl = _find_value_right_of(info, "Wavelength [nm]")
    return PlateRead(
        path=path.name,
        instrument=_find_value_right_of(info, "Name"),
        serial=_find_value_right_of(info, "Serial number:"),
        measured_at=_find_value_right_of(info, "Execution time"),
        wavelength_nm=int(wl) if wl.isdigit() else 0,
        assay_type=_find_value_right_of(info, "Assay type"),
        plate_template=_find_value_right_of(info, "Plate template"),
        wells=wells,
        layout_labelled=layout_labelled,
        standard_curve=curve,
    )
