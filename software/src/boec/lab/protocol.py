"""The well -> condition map, recovered from the differentiation protocol .docx files.

``BO-PURPOSE.md`` marks 83 files ``blocked_needs_keymap``: real acquisitions whose
filenames are well IDs, with the conditions those wells received living only in
``raw/protocols/IPSC分化EC-{2,3}.docx``. This module reads the docx.

A .docx is a zip of XML, so no new dependency is needed -- ``zipfile`` plus
``xml.etree`` is the whole reader. Cell text is joined **per paragraph**, because the
tables put "CHIR 6μM" and "KODMEM 3ml/well" in separate paragraphs of one cell and a
naive concatenation yields ``CHIR 6μMKODMEM``.

What the extraction shows, and what it costs: protocol v3's five wells are *not* a
clean factorial. Terminal medium is perfectly confounded with the timing of the second
CHIR dose -- every well dosed on Day 2 went to 10%FBS+EGM2 and every well dosed on Day 3
stayed on EC induction. Only the BMP4 contrast is estimable (Well 1 vs 3, Well 2 vs 4).
:func:`confounded_factor_pairs` reports this so a campaign built on these wells cannot
quietly claim to separate the two.
"""

from __future__ import annotations

import re
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime
from itertools import combinations
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

#: Cell markers. 传代 = passaged, 分选 = sorted (FACS), X = well no longer running.
PASSAGE = "传代"
SORT = "分选"
INACTIVE = "X"
EMPTY = "/"

_CHIR = re.compile(r"CHIR\s*([\d.]+)\s*[μµu]M", re.I)
_BMP4 = re.compile(r"BMP4\s*([\d.]+)\s*ng/ml", re.I)
_MEDIA = (
    ("10%FBS + EGM2", "fbs10_egm2"),
    ("N2B27 induction", "n2b27_induction"),
    ("EC induction", "ec_induction"),
    ("KODMEM", "kodmem"),
    ("N2B27", "n2b27"),
)


@dataclass(frozen=True)
class DayEntry:
    """One well on one day."""

    day: int
    on: date | None
    raw: str
    chir_uM: float | None = None
    bmp4_ng_ml: float | None = None
    medium: str | None = None
    passaged: bool = False
    sorted_by_facs: bool = False
    active: bool = True


@dataclass(frozen=True)
class WellSchedule:
    """One row of the protocol table."""

    well: str
    entries: tuple[DayEntry, ...]

    @property
    def chir_schedule(self) -> tuple[tuple[int, float], ...]:
        """``((day, uM), ...)`` for every day CHIR was given."""
        return tuple((e.day, e.chir_uM) for e in self.entries if e.chir_uM is not None)

    @property
    def bmp4_ng_ml(self) -> float:
        """Dose if BMP4 appears anywhere in the schedule, else 0.0 -- the factor level."""
        doses = [e.bmp4_ng_ml for e in self.entries if e.bmp4_ng_ml is not None]
        return float(doses[0]) if doses else 0.0

    @property
    def terminal_medium(self) -> str | None:
        """Last medium named before the well stops or is sorted."""
        media = [e.medium for e in self.entries if e.medium and e.active]
        return media[-1] if media else None

    @property
    def sort_day(self) -> int | None:
        for e in self.entries:
            if e.sorted_by_facs:
                return e.day
        return None

    @property
    def last_active_day(self) -> int | None:
        days = [e.day for e in self.entries if e.active]
        return max(days) if days else None

    def active_on(self, when: date) -> bool:
        return any(e.on == when and e.active for e in self.entries)


@dataclass(frozen=True)
class Protocol:
    """One ``IPSC分化EC-*.docx``."""

    path: str
    title: str
    wells: tuple[WellSchedule, ...]

    def well(self, name: str) -> WellSchedule | None:
        key = name.strip().lower().replace(" ", "")
        for w in self.wells:
            if w.well.strip().lower().replace(" ", "") == key:
                return w
        return None

    @property
    def running_wells(self) -> tuple[WellSchedule, ...]:
        """Wells that ever received anything. ``Well 6`` is X on every day of v3."""
        return tuple(w for w in self.wells if any(e.active for e in w.entries))


def _cell_text(tc: ET.Element) -> str:
    """Join paragraphs with a separator so ``CHIR 6μM`` and ``KODMEM`` stay distinct."""
    paras = []
    for p in tc.iter(W + "p"):
        txt = "".join(t.text or "" for t in p.iter(W + "t")).strip()
        if txt:
            paras.append(txt)
    return " ; ".join(paras)


def _parse_date(raw: str) -> date | None:
    raw = raw.strip()
    for fmt in ("%d/%m/%y", "%d/%m/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _parse_cell(day: int, on: date | None, raw: str) -> DayEntry:
    txt = raw.strip()
    inactive = txt.upper() == INACTIVE or txt == ""
    chir = _CHIR.search(txt)
    bmp4 = _BMP4.search(txt)
    medium = None
    for needle, tag in _MEDIA:
        if needle.lower() in txt.lower():
            medium = tag
            break
    return DayEntry(
        day=day,
        on=on,
        raw=txt,
        chir_uM=float(chir.group(1)) if chir else None,
        bmp4_ng_ml=float(bmp4.group(1)) if bmp4 else None,
        medium=medium,
        passaged=PASSAGE in txt,
        sorted_by_facs=SORT in txt,
        active=not inactive,
    )


def _tables(root: ET.Element) -> list[list[list[str]]]:
    out = []
    for tbl in root.iter(W + "tbl"):
        rows = []
        for tr in tbl.findall(W + "tr"):
            rows.append([_cell_text(tc) for tc in tr.findall(W + "tc")])
        out.append(rows)
    return out


def parse_protocol(path: Path) -> Protocol:
    """Read a protocol docx into per-well day schedules.

    The document is split across two tables (Days 1-10 and Day 11 onward) with the same
    well rows; they are stitched by well name so a schedule spans the whole run.
    """
    path = Path(path)
    root = ET.fromstring(zipfile.ZipFile(path).read("word/document.xml"))

    title = ""
    for p in root.iter(W + "p"):
        txt = "".join(t.text or "" for t in p.iter(W + "t")).strip()
        if txt:
            title = txt
            break

    per_well: dict[str, list[DayEntry]] = {}
    for table in _tables(root):
        if len(table) < 3:
            continue
        day_row, date_row = table[0], table[1]
        days: list[int] = []
        for cell in day_row[1:]:
            m = re.search(r"Day\s*(\d+)", cell)
            days.append(int(m.group(1)) if m else -1)
        dates = [_parse_date(c) for c in date_row[1:]]

        for row in table[2:]:
            if not row:
                continue
            name = row[0].strip()
            if not name or name in {"备注"}:  # 备注 = remarks row, not a well
                continue
            entries = per_well.setdefault(name, [])
            for j, cell in enumerate(row[1:]):
                if j >= len(days) or days[j] < 0:
                    continue
                on = dates[j] if j < len(dates) else None
                entries.append(_parse_cell(days[j], on, cell))

    wells = tuple(
        WellSchedule(well=name, entries=tuple(sorted(e, key=lambda x: x.day)))
        for name, e in per_well.items()
    )
    return Protocol(path=path.name, title=title, wells=wells)


def factor_table(protocol: Protocol) -> list[dict]:
    """One row per running well: the factors a campaign could actually use."""
    rows = []
    for w in protocol.running_wells:
        sched = w.chir_schedule
        rows.append(
            {
                "protocol": protocol.path,
                "well": w.well,
                "chir_schedule": ";".join(f"d{d}:{v:g}uM" for d, v in sched),
                "chir_second_dose_day": sched[1][0] if len(sched) > 1 else None,
                "chir_n_doses": len(sched),
                "bmp4_ng_ml": w.bmp4_ng_ml,
                "terminal_medium": w.terminal_medium,
                "passaged": any(e.passaged for e in w.entries),
                "sort_day": w.sort_day,
                "last_active_day": w.last_active_day,
            }
        )
    return rows


def confounded_factor_pairs(rows: list[dict], factors: list[str]) -> list[tuple[str, str]]:
    """Factor pairs that vary together across wells and so cannot be separated.

    A pair is confounded when knowing one factor's level determines the other's on
    every well in the design. With five wells and three factors this is not a corner
    case -- it is the actual state of protocol v3.
    """
    out = []
    for a, b in combinations(factors, 2):
        mapping: dict[object, object] = {}
        reverse: dict[object, object] = {}
        ok = True
        for r in rows:
            av, bv = r.get(a), r.get(b)
            if av in mapping and mapping[av] != bv:
                ok = False
                break
            if bv in reverse and reverse[bv] != av:
                ok = False
                break
            mapping[av] = bv
            reverse[bv] = av
        if ok and len({r.get(a) for r in rows}) > 1:
            out.append((a, b))
    return out
