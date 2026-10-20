#!/usr/bin/env python3
"""Build report V8 from the submitted V7.

V7 stays untouched. Chapters 1-3 keep their semester-7 structure and get
targeted corrections; Chapters 4-6 are rebuilt from report_v8_content.py.
Paragraph, heading, caption and table formatting is cloned from V7 so the
new text matches the document.

    .venv/bin/python docs/figures/make_figures.py
    .venv/bin/python docs/build_report_v8.py build docs/SiteSafe_FYP_Report_V7.docx docs/SiteSafe_FYP_Report_V8.docx
    soffice --headless --convert-to pdf --outdir <dir> docs/SiteSafe_FYP_Report_V8.docx
    .venv/bin/python docs/build_report_v8.py finalize docs/SiteSafe_FYP_Report_V8.docx <dir>/SiteSafe_FYP_Report_V8.pdf docs/SiteSafe_FYP_Report_V8.docx

The finalize pass writes measured page numbers into the contents and the
lists of figures and tables (run the PDF conversion again afterwards).
"""

from __future__ import annotations

import argparse
import sys
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.table import Table

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS))
import report_v8_content as C  # noqa: E402
import update_fyp_report as U  # noqa: E402

FIGURES = DOCS / "figures"


def style_of(element) -> str:
    p_pr = element.find(qn("w:pPr"))
    style = p_pr.find(qn("w:pStyle")) if p_pr is not None else None
    return style.get(qn("w:val")) if style is not None else ""


def text_of(element) -> str:
    return "".join(t.text or "" for t in element.iter(qn("w:t"))).strip()


def has_page_break(element) -> bool:
    return any(br.get(qn("w:type")) == "page" for br in element.iter(qn("w:br")))


class Templates:
    """Formatting samples cloned from V7 before its Chapter 4-6 bodies go."""

    def __init__(self, doc: Document):
        self.h2 = deepcopy(U.find_paragraph(doc, "4.1 Development Environment")._p)
        self.h3 = deepcopy(U.find_paragraph(doc, "4.3.1 Dataset and Classes")._p)
        self.body = deepcopy(U.find_paragraph(doc, "The verified development environment combines", exact=False)._p)
        self.table_caption = deepcopy(U.find_paragraph(doc, "Table 4.1: Development Environment Summary")._p)
        figure_caption = U.find_paragraph(doc, "Figure 4.2: YOLOv11 Training Pipeline")
        self.figure_caption = deepcopy(figure_caption._p)
        image = figure_caption._p.getprevious()
        assert image.findall(".//" + qn("w:drawing")), "Figure 4.2 caption is not preceded by its image"
        self.image = deepcopy(image)
        self.table = deepcopy(U.table_after_caption(doc, "Table 4.1: Development Environment Summary")._tbl)


def paragraph(template, text: str):
    element = U.clone_paragraph(type("P", (), {"_p": template})(), text)
    return element


def figure(doc: Document, templates: Templates, filename: str, width: float):
    path = FIGURES / filename
    if not path.exists():
        raise SystemExit(f"Missing figure {path}; run docs/figures/make_figures.py")
    element = deepcopy(templates.image)
    for child in list(element):
        if child.tag != qn("w:pPr"):
            element.remove(child)
    scratch = doc.add_paragraph()
    run = scratch.add_run()
    run.add_picture(str(path), width=Inches(width))
    element.append(run._r)
    scratch._p.getparent().remove(scratch._p)
    return element


def table(doc: Document, templates: Templates, rows, widths, font_size):
    if abs(sum(widths) - 6.0) > 0.05:
        raise AssertionError(f"Table widths sum to {sum(widths)}, expected 6.0 in: {rows[0]}")
    tbl = deepcopy(templates.table)
    trs = tbl.findall(qn("w:tr"))
    header_tr, body_tr = trs[0], trs[1]
    for tr in trs:
        tbl.remove(tr)

    def build(tr_template, values):
        tr = deepcopy(tr_template)
        cells = tr.findall(qn("w:tc"))
        for tc in cells:
            tr.remove(tc)
        for _ in values:
            tr.append(deepcopy(cells[0]))
        return tr

    tbl.append(build(header_tr, rows[0]))
    for values in rows[1:]:
        if len(values) != len(rows[0]):
            raise AssertionError(f"Row {values} does not match header {rows[0]}")
        tbl.append(build(body_tr, values))
    wrapper = Table(tbl, doc._body)
    for r, values in enumerate(rows):
        for cell, value in zip(wrapper.rows[r].cells, values):
            U.set_cell_text(cell, value, header=r == 0, size=font_size)
    U.set_repeat_header(wrapper.rows[0])
    for row in wrapper.rows:
        keep_row_together(row)
    U.set_table_geometry(wrapper, widths)
    return tbl


def keep_row_together(row) -> None:
    """A row moves to the next page whole instead of leaving a blank band."""
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = tr_pr.find(qn("w:cantSplit"))
    if cant_split is None:
        # CT_TrPrBase is an unordered choice, but w:ins/w:del must follow it.
        cant_split = tr_pr.makeelement(qn("w:cantSplit"), {})
        tr_pr.insert(0, cant_split)
    # The V7 template rows carry an explicit w:val="0" (splitting allowed).
    cant_split.set(qn("w:val"), "true")


def render_blocks(doc: Document, templates: Templates, blocks) -> list:
    elements = []
    for block in blocks:
        kind = block[0]
        if kind == "h2":
            elements.append(paragraph(templates.h2, block[1]))
        elif kind == "h3":
            elements.append(paragraph(templates.h3, block[1]))
        elif kind == "p":
            elements.append(paragraph(templates.body, block[1]))
        elif kind == "fig":
            _, filename, width, caption = block
            elements.append(figure(doc, templates, filename, width))
            elements.append(paragraph(templates.figure_caption, caption))
        elif kind == "table":
            _, caption, rows, widths, font_size = block
            elements.append(paragraph(templates.table_caption, caption))
            elements.append(table(doc, templates, rows, widths, font_size))
        else:
            raise AssertionError(f"Unknown block {kind!r}")
        if kind in ("h2", "h3", "fig"):
            # Headings stay with their text, images with their captions.
            keep_with_next(elements[-2] if kind == "fig" else elements[-1])
    return elements


def keep_with_next(element) -> None:
    p_pr = element.find(qn("w:pPr"))
    if p_pr is None:
        p_pr = element.makeelement(qn("w:pPr"), {})
        element.insert(0, p_pr)
    if p_pr.find(qn("w:keepNext")) is None:
        from docx.text.paragraph import Paragraph

        Paragraph(element, None).paragraph_format.keep_with_next = True


def replace_chapter_body(doc: Document, first_heading: str, elements) -> None:
    """Remove a chapter's body, from its first section heading up to the
    blank heading or page break that leads into the next chapter, and put
    ``elements`` in its place."""
    node = U.find_paragraph(doc, first_heading)._p
    removed = 0
    while True:
        if node is None:
            raise AssertionError(f"Chapter starting at {first_heading!r} has no end marker")
        is_end = node.tag == qn("w:p") and not text_of(node) and (style_of(node) == "Heading1" or has_page_break(node))
        if is_end:
            break
        if node.findall(".//" + qn("w:sectPr")):
            raise AssertionError(f"Section break inside chapter body at {text_of(node)!r}")
        following = node.getnext()
        node.getparent().remove(node)
        removed += 1
        node = following
    U.insert_before(node, elements)
    print(f"  {first_heading.split()[0][0]}: removed {removed} elements, inserted {len(elements)}")


def edit_chapters_1_to_3(doc: Document) -> None:
    for prefix, text in C.CHAPTER_1_TO_3_EDITS:
        U.set_paragraph_text(U.find_paragraph(doc, prefix, exact=False), text)
    comparison = U.table_after_caption(doc, "Table 2.1: Comparison of Existing Systems/Devices Against Site-Safe")
    last = comparison.rows[-1]
    assert last.cells[0].text.strip().startswith("Site-Safe"), "Table 2.1 last row is not Site-Safe"
    size = last.cells[0].paragraphs[0].runs[0].font.size
    for cell, value in zip(last.cells, C.TABLE_21_SITE_SAFE_ROW):
        U.set_cell_text(cell, value, size=size.pt if size else 9.0)


def replace_abstract(doc: Document) -> list:
    first = U.find_paragraph(doc, "Construction sites need evidence", exact=False)
    rest = [first._p.getnext(), first._p.getnext().getnext()]
    assert all(text_of(p) for p in rest), "Abstract is expected to have three paragraphs"
    U.set_paragraph_text(first, C.ABSTRACT[0])
    for element, text in zip(rest, C.ABSTRACT[1:]):
        for child in list(element):
            if child.tag != qn("w:pPr"):
                element.remove(child)
        run = paragraph(element, text).find(qn("w:r"))
        element.append(run)
    return [first._p, *rest]


def edit_abbreviations(doc: Document) -> None:
    start = U.find_paragraph(doc, "LIST OF ABBREVIATIONS")._p
    entries = []
    node = start.getnext()
    while node is not None and node.tag == qn("w:p") and text_of(node):
        entries.append(node)
        node = node.getnext()
    template = entries[0]
    for entry in entries:
        if text_of(entry).split()[0] in C.ABBREVIATIONS_REMOVE:
            entry.getparent().remove(entry)
    for short, long in C.ABBREVIATIONS_ADD:
        current = [e for e in entries if e.getparent() is not None]
        # Each entry is a bold "ABBR  " run followed by the expansion.
        new = deepcopy(template)
        abbr_run, long_run = new.findall(qn("w:r"))[:2]
        abbr_run.find(qn("w:t")).text = f"{short}  "
        long_run.find(qn("w:t")).text = long
        after = next((e for e in current if text_of(e).split()[0].lower() > short.lower()), None)
        if after is not None:
            after.addprevious(new)
        else:
            current[-1].addnext(new)
        entries.append(new)


def edit_references(doc: Document) -> None:
    for prefix, text in C.REFERENCE_EDITS:
        U.set_paragraph_text(U.find_paragraph(doc, prefix, exact=False), text)
    last = U.find_paragraph(doc, "[20] ", exact=False)._p
    for text in C.REFERENCES_ADD:
        new = paragraph(last, text)
        last.addnext(new)
        last = new


def chapter_title_pages(doc: Document) -> None:
    """Guideline: each chapter opens with a title page holding only the
    chapter number (18 pt bold) and name (22 pt bold)."""
    paragraphs = doc.paragraphs
    for number, title in U.CHAPTER_TITLES.items():
        idx = next(i for i, p in enumerate(paragraphs) if p.text.strip() == f"Chapter {number}")
        label, name = paragraphs[idx], paragraphs[idx + 1]
        assert name.text.strip() == title, f"Chapter {number} title is {name.text!r}"
        for p, size in ((label, 18), (name, 22)):
            p.alignment = 1  # centre
            for run in p.runs:
                U.set_run_font(run, size=size, bold=True)
        # Chapters 1-4 centre the title with blank lines above it; 5 and 6 have none.
        if not paragraphs[idx - 1].text.strip() and not paragraphs[idx - 2].text.strip():
            label.paragraph_format.space_before = None
        else:
            label.paragraph_format.space_before = Pt(220)
        first_section = next(p for p in paragraphs[idx + 2:] if p.text.strip() and p.style.name == "Heading 2")
        first_section.paragraph_format.page_break_before = True


def build(input_path: Path, output_path: Path) -> None:
    doc = Document(input_path)
    templates = Templates(doc)
    abstract = replace_abstract(doc)
    edit_chapters_1_to_3(doc)
    replace_chapter_body(doc, "4.1 Development Environment", render_blocks(doc, templates, C.CHAPTER_4))
    replace_chapter_body(doc, "5.1 Testing Approach", render_blocks(doc, templates, C.CHAPTER_5))
    replace_chapter_body(doc, "6.1 Conclusion", render_blocks(doc, templates, C.CHAPTER_6))
    edit_abbreviations(doc)
    edit_references(doc)
    U.normalize_typography(doc)
    for element in abstract:
        for run in element.iter(qn("w:r")):
            from docx.text.run import Run

            U.set_run_font(Run(run, None), size=12)
    chapter_title_pages(doc)
    U.write_front_matter(doc)
    doc.core_properties.revision = (doc.core_properties.revision or 0) + 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output_path)
    print(f"wrote {output_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("input", type=Path)
    b.add_argument("output", type=Path)
    f = sub.add_parser("finalize")
    f.add_argument("input", type=Path)
    f.add_argument("pdf", type=Path)
    f.add_argument("output", type=Path)
    args = ap.parse_args()
    if args.command == "build":
        if args.input.resolve() == args.output.resolve():
            raise SystemExit("Refusing to overwrite the input report")
        build(args.input, args.output)
    else:
        U.finalize_report(args.input, args.pdf, args.output)


if __name__ == "__main__":
    main()
