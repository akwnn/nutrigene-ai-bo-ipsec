from __future__ import annotations

from pathlib import Path
import hashlib
import json
from zipfile import ZipFile

from lxml import etree

from scripts.build_manuscript_docx import build


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W, "m": M}


def _document_xml(path: Path) -> etree._Element:
    with ZipFile(path) as archive:
        return etree.fromstring(archive.read("word/document.xml"))


def _build(tmp_path: Path, markdown: str) -> etree._Element:
    source = tmp_path / "manuscript.md"
    output = tmp_path / "manuscript.docx"
    source.write_text(markdown, encoding="utf-8")
    build(source, output)
    return _document_xml(output)


def test_math_is_written_as_native_word_equations(tmp_path):
    root = _build(
        tmp_path,
        """# Test manuscript

Inline $x_i^2$ expression.

\\[
\\frac{x_i}{y_i}
\\]
""",
    )

    text = "".join(root.itertext())
    assert "\\frac" not in text
    assert root.xpath("count(.//m:oMath)", namespaces=NS) == 2


def test_square_root_equation_has_complete_omml_radical_structure(tmp_path):
    root = _build(
        tmp_path,
        "# Test manuscript\n\nInline $x_i^*=\\sqrt{\\mathrm{EC}_{50,i}\\mathrm{IC}_{50,i}}$.\n",
    )

    radical = root.xpath(".//m:rad", namespaces=NS)[0]
    assert radical.xpath("./m:radPr/m:degHide", namespaces=NS)
    assert radical.xpath("./m:deg", namespaces=NS)


def test_roman_math_labels_are_preserved_as_single_words(tmp_path):
    root = _build(
        tmp_path,
        "# Test manuscript\n\nInline $\\widehat{\\mathrm{Var}}(y)$ expression.\n",
    )

    equation_text = root.xpath(".//m:oMath[1]//m:t/text()", namespaces=NS)
    assert "Var" in equation_text


def test_method_table_reserves_width_for_design_and_keeps_rows_intact(tmp_path):
    root = _build(
        tmp_path,
        """# Test manuscript

| Method | Design | Wells | Rounds | Primary purpose |
|---|---|---:|---:|---|
| SPADE | 40-point LHS plus eight model-directed points | 48 | 2 | Region mapping and certification |
""",
    )

    widths = [
        int(value)
        for value in root.xpath(".//w:tbl[1]/w:tblGrid/w:gridCol/@w:w", namespaces=NS)
    ]
    assert widths == [2200, 3000, 760, 900, 2500]
    rows = root.xpath(".//w:tbl[1]/w:tr", namespaces=NS)
    assert all(row.xpath("./w:trPr/w:cantSplit", namespaces=NS) for row in rows)


def test_page_bottom_margin_keeps_body_clear_of_footer(tmp_path):
    root = _build(tmp_path, "# Test manuscript\n\nBody text.\n")

    bottom = int(root.xpath("string(.//w:sectPr/w:pgMar/@w:bottom)", namespaces=NS))
    assert bottom >= 2160


def test_manuscript_title_has_native_title_style(tmp_path):
    root = _build(tmp_path, "# Test manuscript\n\nBody text.\n")
    assert root.xpath("string(.//w:body/w:p[1]/w:pPr/w:pStyle/@w:val)", namespaces=NS) == "Title"


def test_title_style_has_no_decorative_border(tmp_path):
    _build(tmp_path, "# Test manuscript\n\nBody text.\n")
    with ZipFile(tmp_path / "manuscript.docx") as archive:
        styles = etree.fromstring(archive.read("word/styles.xml"))
    assert not styles.xpath('.//w:style[@w:styleId="Title"]//w:pBdr', namespaces=NS)


def test_submission_copy_keeps_captions_but_omits_embedded_figures(tmp_path):
    source = tmp_path / "manuscript.md"
    output = tmp_path / "submission.docx"
    source.write_text("# Paper\n\n![Figure](separately-uploaded.png)\n\n**Fig 1. Evidence.** Caption.\n")
    build(source, output, include_figures=False)
    root = _document_xml(output)
    assert "Fig 1. Evidence." in "".join(root.itertext())
    assert not root.xpath(".//w:drawing", namespaces=NS)


def test_tables_have_explicit_light_gray_borders(tmp_path):
    root = _build(tmp_path, "# Paper\n\n| Method | Score |\n|---|---|\n| SPADE | 0.18 |\n")
    borders = root.xpath(".//w:tblPr/w:tblBorders/*", namespaces=NS)
    assert len(borders) == 6
    assert all(edge.get(f"{{{W}}}color") == "D9D9D9" for edge in borders)


def test_table_caption_stays_with_its_table(tmp_path):
    root = _build(tmp_path, "# Paper\n\n**Table 3. Target means.** Caption text.\n\n| Method | Score |\n|---|---|\n| SPADE | 0.18 |\n")
    table = root.xpath(".//w:body/w:tbl", namespaces=NS)[0]
    caption = table.getprevious()
    assert "Table 3." in "".join(caption.itertext())
    assert caption.xpath("./w:pPr/w:keepNext", namespaces=NS)
    assert caption.xpath("./w:pPr/w:keepLines", namespaces=NS)


def test_build_records_source_builder_and_output_hashes(tmp_path):
    source = tmp_path / "paper.md"
    output = tmp_path / "paper.docx"
    source.write_text("# Paper\n\nBody text.\n")
    build(source, output, include_figures=False)
    manifest_path = output.with_suffix(".docx.manifest.json")
    assert manifest_path.is_file(), "Word output needs source-bound provenance"
    manifest = json.loads(manifest_path.read_text())
    assert manifest["source_sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest["output_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert manifest["builder_sha256"] == hashlib.sha256(Path("scripts/build_manuscript_docx.py").read_bytes()).hexdigest()
    assert manifest["include_figures"] is False
    assert manifest["image_sha256"] == {}


def test_cover_letter_uses_letter_spacing_without_manuscript_line_numbers(tmp_path):
    source = tmp_path / "letter.md"
    output = tmp_path / "letter.docx"
    source.write_text("# Cover letter\n\nDear Editors,\n\nPlease consider our article.\n")
    build(source, output, include_figures=False, cover_letter=True)
    root = _document_xml(output)
    assert not root.xpath(".//w:lnNumType", namespaces=NS)
    with ZipFile(output) as archive:
        styles = etree.fromstring(archive.read("word/styles.xml"))
    assert styles.xpath('string(.//w:style[@w:styleId="Normal"]/w:pPr/w:spacing/@w:line)', namespaces=NS) == "240"
    manifest = json.loads(output.with_suffix(".docx.manifest.json").read_text())
    assert manifest["cover_letter"] is True


def test_abstract_starts_after_the_title_page(tmp_path):
    root = _build(tmp_path, "# Paper\n\nAuthors: Example\n\n## Abstract\n\nSummary.\n")
    heading = root.xpath('.//w:p[w:r/w:t="Abstract"]', namespaces=NS)[0]
    assert heading.getprevious().xpath('.//w:br[@w:type="page"]', namespaces=NS)
