"""Assemble every reader in this package into the derived tables under ``data/lab/derived/``.

The contract of this module is that **nothing it writes is optimizer input**. Files
named ``candidate_*`` hold numbers software produced; promoting one into a campaign CSV
is a human act, because the open judgement calls listed in :mod:`boec.lab.gating` are
not arithmetic. What the pipeline guarantees is that every one of the 305 files has been
opened, that what was found is recorded, and that the two derived metrics never share a
column.

Controls are matched **within a directory and day**: an unstained tube from 21 July
cannot set the positivity threshold for an 6 August acquisition, because gain settings
and cell state both moved. A directory with no unstained control yields no percentages
rather than borrowed ones.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date
from pathlib import Path

import pandas as pd

from .fcs import read_summary
from .gating import percent_positive, resolve_cd31_channel
from .imaging import (
    METRIC_NAME as COVERAGE_METRIC,
    METRIC_PROTOCOL as COVERAGE_PROTOCOL,
    METRIC_UNIT as COVERAGE_UNIT,
    analyse_image,
    read_sidecar,
    sidecar_for,
)
from .manifest import build_file_index, load_manifest, verify_checksums
from .plate import read_plate
from .protocol import confounded_factor_pairs, factor_table, parse_protocol

DERIVED = "derived"

#: Corrected from the ``novocyte-`` string in the draft overlay. Every one of the 52
#: FCS files reports ``$CYT = CytoFLEX LX``; see :mod:`boec.lab.fcs`.
FLOW_METRIC = ("CD31_pct_flow", "percent_of_parent", "cytoflexlx-cd31-cd140a-2026-08-06")

#: Filename stems that are controls rather than conditions, lowercased.
CONTROL_STEMS = {"us", "us-2", "us-23", "us-old", "us-new", "iso", "before", "before2"}

COATING_DOSES = ("0.5", "1", "2.5", "5", "10", "20")
DOSE_LOW, DOSE_HIGH = 0.5, 20.0

#: The 2026-08-04 Leica frames that match the 12 flow conditions by coating and dose.
MORPHOLOGY_IMAGES = {
    ("fibronectin", 0.5): "fib 0-5", ("fibronectin", 1.0): "fib 1",
    ("fibronectin", 2.5): "fib 2-5", ("fibronectin", 5.0): "fib5",
    ("fibronectin", 10.0): "fib10", ("fibronectin", 20.0): "fib20",
    ("vitronectin", 0.5): "vtn 0-5", ("vitronectin", 1.0): "vtn 1",
    ("vitronectin", 2.5): "vtn 2-5", ("vitronectin", 5.0): "vtn5",
    ("vitronectin", 10.0): "vtn 10", ("vitronectin", 20.0): "vtn 20",
}


def coded_dose(dose_ug_ml: float) -> float:
    """Coded on this box's own range. NOT the Phase 1/2 ECM cube."""
    return (dose_ug_ml - DOSE_LOW) / (DOSE_HIGH - DOSE_LOW)


def is_control(path: Path) -> bool:
    return path.stem.lower() in CONTROL_STEMS


def find_control(directory: Path) -> Path | None:
    """The unstained tube for a directory, or ``None``.

    An exact ``us``/``US`` wins. Otherwise the first by sorted name -- so
    ``Exp_20260806_1`` resolves to ``US-new`` over ``US-old``. That tie-break is
    arbitrary, so the chosen control travels in the ``control`` column of every output
    row rather than being implicit.

    Measured cost of the tie-break on this drop: gating ``well 3`` against ``US-new``
    gives 8.56% and against ``US-old`` 10.14%, about 1.6pp. That is small next to the
    ~4x gap between the protocol wells and the coating panel, which is why that gap can
    be called real rather than an artefact of control choice.
    """
    fcs = sorted(directory.glob("*.fcs"))
    unstained = [p for p in fcs if p.stem.lower().startswith("us")]
    if not unstained:
        return None
    exact = [p for p in unstained if p.stem.lower() == "us"]
    return exact[0] if exact else unstained[0]


def file_index_frame(lab_root: Path, *, verify: bool = True) -> pd.DataFrame:
    files = build_file_index(lab_root, verify=verify)
    rows = [asdict(f) | {"checksum_ok": f.checksum_ok, "is_overlay": f.is_overlay} for f in files]
    return pd.DataFrame(rows)


def flow_acquisition_frame(lab_root: Path) -> pd.DataFrame:
    rows = []
    for p in sorted((lab_root / "flow").rglob("*.fcs")):
        s = read_summary(p)
        rows.append(
            {
                "path": p.relative_to(lab_root).as_posix(),
                "directory": p.parent.relative_to(lab_root).as_posix(),
                "tube": p.stem,
                "cytometer": s.cytometer,
                "serial": s.serial,
                "acquired_date": s.acquired_date.isoformat() if s.acquired_date else None,
                "acquired_time": s.acquired_time.isoformat() if s.acquired_time else None,
                "events": s.events,
                "parameters": s.parameters,
                "fcs_version": s.fcs_version,
                "spillover_is_identity": s.spillover_is_identity,
                "compensation_applied": False if s.spillover_is_identity else None,
                "aborted": s.aborted,
                "is_control": is_control(p),
                "operator": s.operator,
            }
        )
    return pd.DataFrame(rows)


def flow_positivity_frame(lab_root: Path, cd31_detector: str, cd140a_detector: str) -> pd.DataFrame:
    """CD31% and CD140a% for every non-control tube that has a same-day unstained control."""
    rows = []
    for directory in sorted({p.parent for p in (lab_root / "flow").rglob("*.fcs")}):
        control = find_control(directory)
        for p in sorted(directory.glob("*.fcs")):
            summary = read_summary(p)
            base = {
                "path": p.relative_to(lab_root).as_posix(),
                "directory": directory.relative_to(lab_root).as_posix(),
                "tube": p.stem,
                "events": summary.events,
            }
            if summary.aborted:
                rows.append(base | {"status": "aborted_zero_events"})
                continue
            if is_control(p):
                rows.append(base | {"status": "control"})
                continue
            if control is None:
                rows.append(base | {"status": "no_same_day_unstained_control"})
                continue
            cd31 = percent_positive(p, control, cd31_detector)
            cd140a = percent_positive(p, control, cd140a_detector)
            rows.append(
                base
                | {
                    "status": "gated_candidate",
                    "control": control.name,
                    "cd31_detector": cd31_detector,
                    "cd31_pct": round(cd31.pct_positive, 4),
                    "cd31_threshold": round(cd31.threshold, 2),
                    "cd31_pct_p95": round(cd31.sensitivity[95.0], 4),
                    "cd31_pct_p99_9": round(cd31.sensitivity[99.9], 4),
                    "cd31_spread_pp": round(cd31.spread, 4),
                    "cd140a_detector": cd140a_detector,
                    "cd140a_pct": round(cd140a.pct_positive, 4),
                }
            )
    return pd.DataFrame(rows)


def image_feature_frame(lab_root: Path, *, long_edge: int = 1024) -> pd.DataFrame:
    rows = []
    micro = lab_root / "microscopy"
    images = sorted(
        p for p in micro.rglob("*") if p.suffix.lower() in {".jpeg", ".jpg", ".png", ".tif", ".tiff"}
    )
    for p in images:
        f = analyse_image(p, long_edge=long_edge)
        side = sidecar_for(p)
        meta = read_sidecar(side) if side else None
        rows.append(
            {
                "path": p.relative_to(lab_root).as_posix(),
                "day": p.parent.name,
                "instrument": "leica" if "/leica/" in p.as_posix() else "evos",
                "coverage_frac": round(f.coverage, 5),
                "otsu_threshold": round(f.otsu_threshold, 6),
                "otsu_separability": round(f.otsu_separability, 5),
                "coverage_trustworthy": f.coverage_is_trustworthy,
                "focus": round(f.focus, 8),
                "mean_intensity": round(f.mean_intensity, 5),
                "std_intensity": round(f.std_intensity, 5),
                "contrast": meta.contrast if meta else None,
                "objective": meta.objective if meta else None,
                "exposure": meta.exposure if meta else None,
                "gain": meta.gain if meta else None,
                "light_intensity": meta.light_intensity if meta else None,
                "captured": meta.created.isoformat() if meta and meta.created else None,
                "comparability_key": "|".join(str(x) for x in f.comparability_key)
                if f.comparability_key
                else None,
            }
        )
    return pd.DataFrame(rows)


def coating_flow_campaign(positivity: pd.DataFrame) -> pd.DataFrame:
    """The 12 FN/VTN tubes as candidate campaign rows."""
    panel = positivity[
        positivity["directory"].str.endswith("Exp_20260806_cd31-cd140a")
        & (positivity["status"] == "gated_candidate")
    ]
    rows = []
    for _, r in panel.iterrows():
        tube = str(r["tube"])
        coating = "fibronectin" if tube.startswith("f") else "vitronectin"
        dose = float(tube[1:])
        rows.append(
            {
                "file": r["path"],
                "coating": coating,
                "coating_coded": 0.0 if coating == "fibronectin" else 1.0,
                "dose_ug_mL": dose,
                "coded_dose": round(coded_dose(dose), 10),
                "metric_name": FLOW_METRIC[0],
                "metric_unit": FLOW_METRIC[1],
                "metric_protocol_version": FLOW_METRIC[2],
                "events": r["events"],
                "y_candidate": r["cd31_pct"],
                "y_candidate_p95": r["cd31_pct_p95"],
                "y_candidate_p99_9": r["cd31_pct_p99_9"],
                "y_spread_pp": r["cd31_spread_pp"],
                "y_sd": "",
                "n_replicates": 1,
                "control": r["control"],
                "status": "awaiting_human_signoff",
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["coating", "dose_ug_mL"]).reset_index(drop=True)


def coating_morphology_campaign(images: pd.DataFrame) -> pd.DataFrame:
    """The 12 dose-matched Leica frames as a SEPARATE candidate campaign."""
    rows = []
    for (coating, dose), stem in MORPHOLOGY_IMAGES.items():
        want = f"Leica_2026-08-04 {stem}.jpeg"
        hit = images[images["path"].str.endswith(want)]
        if hit.empty:
            continue
        r = hit.iloc[0]
        rows.append(
            {
                "file": r["path"],
                "coating": coating,
                "coating_coded": 0.0 if coating == "fibronectin" else 1.0,
                "dose_ug_mL": dose,
                "coded_dose": round(coded_dose(dose), 10),
                "metric_name": COVERAGE_METRIC,
                "metric_unit": COVERAGE_UNIT,
                "metric_protocol_version": COVERAGE_PROTOCOL,
                "y_candidate": r["coverage_frac"],
                "otsu_separability": r["otsu_separability"],
                "trustworthy": r["coverage_trustworthy"],
                "comparability_key": r["comparability_key"],
                "y_sd": "",
                "n_replicates": 1,
                "status": "awaiting_human_signoff",
            }
        )
    out = pd.DataFrame(rows)
    return out.sort_values(["coating", "dose_ug_mL"]).reset_index(drop=True)


def protocol_frame(lab_root: Path) -> tuple[pd.DataFrame, dict]:
    rows: list[dict] = []
    confounding: dict[str, list] = {}
    for docx in sorted((lab_root / "protocols").glob("*.docx")):
        proto = parse_protocol(docx)
        table = factor_table(proto)
        rows.extend(table)
        confounding[docx.name] = [
            list(pair)
            for pair in confounded_factor_pairs(
                table, ["chir_second_dose_day", "bmp4_ng_ml", "terminal_medium", "passaged"]
            )
        ]
    return pd.DataFrame(rows), confounding


def build_all(lab_root: Path, *, verify: bool = True, long_edge: int = 1024) -> dict:
    """Run every reader and write ``data/lab/derived/``. Returns the run summary."""
    lab_root = Path(lab_root)
    out_dir = lab_root / DERIVED
    out_dir.mkdir(exist_ok=True)

    index = file_index_frame(lab_root, verify=verify)
    index.to_csv(out_dir / "file_index.csv", index=False)

    checks = verify_checksums(
        build_file_index(lab_root, verify=verify), load_manifest(lab_root / "MANIFEST.sha256")
    )

    flow = flow_acquisition_frame(lab_root)
    flow.to_csv(out_dir / "flow_acquisitions.csv", index=False)

    identity = resolve_cd31_channel(lab_root / "flow" / "2026-07-28" / "Exp_20260728_1")
    cd140a = "Y585-A"
    (out_dir / "channel_identity.json").write_text(
        json.dumps(identity.as_dict() | {"cd140a_detector_by_elimination": cd140a}, indent=2),
        encoding="utf-8",
    )

    positivity = flow_positivity_frame(lab_root, identity.cd31_detector, cd140a)
    positivity.to_csv(out_dir / "flow_positivity_candidate.csv", index=False)

    images = image_feature_frame(lab_root, long_edge=long_edge)
    images.to_csv(out_dir / "image_features.csv", index=False)

    flow_campaign = coating_flow_campaign(positivity)
    flow_campaign.to_csv(out_dir / "candidate_campaign_coating_flow.csv", index=False)

    morph_campaign = coating_morphology_campaign(images)
    morph_campaign.to_csv(out_dir / "candidate_campaign_coating_morphology.csv", index=False)

    wells, confounding = protocol_frame(lab_root)
    wells.to_csv(out_dir / "protocol_wellmap.csv", index=False)

    plate_path = next((lab_root / "plate-reader").glob("*.xlsx"), None)
    plate_summary = None
    if plate_path is not None:
        plate = read_plate(plate_path)
        plate_summary = {
            "path": plate.path,
            "instrument": plate.instrument,
            "serial": plate.serial,
            "measured_at": plate.measured_at,
            "wavelength_nm": plate.wavelength_nm,
            "assay_type": plate.assay_type,
            "plate_template": plate.plate_template,
            "wells_read": plate.n_wells,
            "layout_labelled": plate.layout_labelled,
            "looks_like_bca": plate.looks_like_bca,
            "standard_curve_rows": list(plate.standard_curve.row_labels)
            if plate.standard_curve
            else None,
            "verdict": (
                "BCA total-protein plate (562 nm) with an unlabelled layout. Not a CD31 "
                "readout under any labelling, so it can never join the flow campaign."
            ),
        }
        (out_dir / "plate_reader.json").write_text(
            json.dumps(plate_summary, indent=2), encoding="utf-8"
        )

    summary = {
        "generated_by": "boec.lab.dataset.build_all",
        "lab_root": str(lab_root),
        "files_indexed": int(len(index)),
        "checksums_verified": checks.ok,
        "checksums_mismatched": checks.mismatched,
        "flow_files": int(len(flow)),
        "flow_aborted": int(flow["aborted"].sum()),
        "flow_gated_candidates": int((positivity["status"] == "gated_candidate").sum()),
        "images_analysed": int(len(images)),
        "cd31_detector": identity.cd31_detector,
        "cd31_margin_pp": round(identity.margin, 4),
        "cd140a_detector": cd140a,
        "protocol_wells": int(len(wells)),
        "protocol_confounding": confounding,
        "plate_reader": plate_summary,
        "flow_metric": list(FLOW_METRIC),
        "coverage_metric": [COVERAGE_METRIC, COVERAGE_UNIT, COVERAGE_PROTOCOL],
        "promotion_rule": (
            "Every y_candidate here is software-derived and unsigned. Promotion into "
            "bo_primary_conditions.csv is a human act -- see data/lab/GATE.md."
        ),
    }
    (out_dir / "RUN.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary
