from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from lxml import etree


ROOT = Path(__file__).resolve().parents[2]
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def _build(tmp_path: Path) -> etree._Element:
    output = tmp_path / "SPADE-MANUSCRIPT.docx"
    completed = subprocess.run(
        [
            sys.executable,
            "software/scripts/build_manuscript_docx.py",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    assert output.is_file()
    with ZipFile(output) as archive:
        return etree.fromstring(archive.read("word/document.xml"))


def test_builder_packages_the_canonical_manuscript(tmp_path: Path) -> None:
    root = _build(tmp_path)
    text = "".join(root.itertext())

    assert text.startswith("From point optimization to operating-region decisions")
    assert "Joseph Yung" in text
    assert "Alana Kwan" in text
    assert "Abstract" in text
    assert "Hall ML, Lin W-H, Ogle BM" in text
    assert root.xpath("count(.//w:tbl)", namespaces=NS) == 3
    assert "**" not in text
    assert "`" not in text


def test_builder_emits_review_ready_page_and_table_contracts(tmp_path: Path) -> None:
    root = _build(tmp_path)

    title_style = root.xpath(
        "string(.//w:body/w:p[1]/w:pPr/w:pStyle/@w:val)", namespaces=NS
    )
    page_width = int(root.xpath("string(.//w:sectPr/w:pgSz/@w:w)", namespaces=NS))
    page_height = int(root.xpath("string(.//w:sectPr/w:pgSz/@w:h)", namespaces=NS))

    assert title_style == "Title"
    assert page_width == 12240
    assert page_height == 15840
    assert root.xpath(".//w:sectPr/w:lnNumType", namespaces=NS)
    rows = root.xpath(".//w:tbl/w:tr", namespaces=NS)
    assert rows
    assert all(row.xpath("./w:trPr/w:cantSplit", namespaces=NS) for row in rows)
    assert all(
        table.xpath("./w:tr[1]/w:trPr/w:tblHeader", namespaces=NS)
        for table in root.xpath(".//w:tbl", namespaces=NS)
    )
