#!/usr/bin/env python3
"""Build report V8 from the submitted V7.

V7 stays untouched. Chapters 1-3 keep their semester-7 structure and get
targeted corrections plus the requirements and workflow sections of
Chapter 3; Chapters 4-6 and the appendices are built from
report_v8_content.py, and the blank approval pages are added to the front
matter.
Paragraph, heading, caption and table formatting is cloned from V7 so the
new text matches the document.

    .venv/bin/python docs/figures/make_figures.py
    .venv/bin/python docs/build_report_v8.py build docs/SiteSafe_FYP_Report_V7.docx docs/SiteSafe_FYP_Report_V8.docx
    osascript docs/word_to_pdf.applescript "$PWD/docs/SiteSafe_FYP_Report_V8.docx" "$PWD/<out>.pdf"
    .venv/bin/python docs/build_report_v8.py finalize docs/SiteSafe_FYP_Report_V8.docx <out>.pdf docs/SiteSafe_FYP_Report_V8.docx

The finalize pass writes measured page numbers into the contents and the
lists of figures and tables (run the PDF conversion again afterwards).
Measure from Microsoft Word, which the report is submitted from: it
paginates differently from LibreOffice (about three more pages), and
LibreOffice also hides layout errors that Word shows, such as an
over-wide table. Close the report in Word before converting, or Word
renders its open, possibly stale, copy.
"""

from __future__ import annotations

import argparse
import re
import sys
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
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
    # A header row never ends a page on its own, and a short table stays whole.
    for row in wrapper.rows[:-1] if len(rows) <= 10 else wrapper.rows[:1]:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next = True
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


def replace_between_headings(doc: Document, heading: str, next_heading: str, elements) -> None:
    """Replace everything between two headings. V7's 3.2.2 list sits in
    Google Docs content controls, which python-docx's paragraphs skip."""
    node = U.find_paragraph(doc, heading)._p.getnext()
    end = U.find_paragraph(doc, next_heading)._p
    while node is not end:
        following = node.getnext()
        node.getparent().remove(node)
        node = following
    U.insert_before(end, elements)


def extend_chapter_3(doc: Document, templates: Templates) -> None:
    replace_between_headings(doc, "3.2.2 Data Flow", "3.3 Module 1: Vision Intelligence",
                             render_blocks(doc, templates, C.DATA_FLOW_322))
    old, new = C.LIMITATIONS_HEADING
    limitations = U.find_paragraph(doc, old)
    U.insert_before(limitations._p, render_blocks(doc, templates, C.CHAPTER_3_ADDITIONS))
    U.set_paragraph_text(limitations, new)


def without_moved_tables(blocks):
    return [b for b in blocks if not (b[0] == "table" and b[1].split(":")[0] in C.MOVED_TABLES)]


def add_appendices(doc: Document, templates: Templates) -> None:
    """Each appendix gets a title page like the chapters', placed between
    Chapter 6 and the References."""
    label = U.find_paragraph(doc, "Chapter 6")._p
    separator = [label.getprevious(), label, label.getnext()]
    assert has_page_break(separator[0]), "Chapter 6 label is not preceded by a page break"
    end = U.find_paragraph(doc, "References")._p.getprevious()
    assert end.tag == qn("w:p") and not text_of(end) and style_of(end) == "Heading1", "No end marker before References"
    for number, title, blocks in C.APPENDICES:
        brk, number_p, title_p = (deepcopy(e) for e in separator)
        for element, text in ((number_p, f"Appendix {number}"), (title_p, title)):
            element.findall(qn("w:r"))[0].find(qn("w:t")).text = text
            for run in element.findall(qn("w:r"))[1:]:
                element.remove(run)
        U.insert_before(end, [brk, number_p, title_p, *render_blocks(doc, templates, blocks)])
    U.find_paragraph(doc, "References").paragraph_format.page_break_before = True


def renumber_tables(doc: Document) -> dict[str, str]:
    """Number the tables left in each chapter consecutively again and point
    every reference ("Table 5.8", "Tables 5.3 to 5.6") at the new number or
    at the appendix table that replaced it."""
    body = list(doc.element.body)
    start = next(i for i, e in enumerate(body) if text_of(e) == "Chapter 1")
    mapping = {old.split()[1]: new.split()[1] for old, new in C.MOVED_TABLES.items()}
    counters: dict[str, int] = {}
    for element in body[start:]:
        match = re.match(r"Table (\d+)\.(\d+):", text_of(element)) if element.tag == qn("w:p") else None
        if match:
            chapter = match.group(1)
            counters[chapter] = counters.get(chapter, 0) + 1
            new = f"{chapter}.{counters[chapter]}"
            if new != f"{chapter}.{match.group(2)}":
                mapping[f"{chapter}.{match.group(2)}"] = new
    reference = re.compile(r"\b(Tables?\s+)(\d+\.\d+(?:(?:\s*,\s*|\s+and\s+|\s+to\s+|\s*[–-]\s*)\d+\.\d+)*)")

    def rewrite(match):
        return match.group(1) + re.sub(r"\d+\.\d+", lambda m: mapping.get(m.group(), m.group()), match.group(2))

    for element in body[start:]:
        for t in element.iter(qn("w:t")):
            if t.text and "Table" in t.text:
                t.text = reference.sub(rewrite, t.text)
    captions = {m.group(1) for e in body[start:] if (m := re.match(r"Table ([\dIVX]+\.\d+):", text_of(e)))}
    for element in body[start:]:
        for paragraph in element.iter(qn("w:p")):
            for match in reference.finditer(text_of(paragraph)):
                for number in re.findall(r"\d+\.\d+", match.group(2)):
                    if number not in captions:
                        raise AssertionError(f"Reference to missing Table {number}: {text_of(paragraph)[:80]!r}")
    print(f"  tables renumbered: {mapping}")
    return mapping


def appendix_title_pages(doc: Document) -> None:
    paragraphs = doc.paragraphs
    for idx, p in enumerate(paragraphs):
        if not re.fullmatch(r"Appendix [IVX]+", p.text.strip()):
            continue
        name = paragraphs[idx + 1]
        for para, size in ((p, 18), (name, 22)):
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
            para.paragraph_format.line_spacing = None
            for run in para.runs:
                U.set_run_font(run, size=size, bold=True)
        p.paragraph_format.space_before = Pt(220)
        first = next(q for q in paragraphs[idx + 2:] if q.text.strip())
        first.paragraph_format.page_break_before = True


def front_paragraph(text: str = "", *, size=12, bold=False, align="both", page_break=False,
                    before=0, after=160, right: str | None = None):
    """A front-matter paragraph; ``right`` goes after a tab at the right margin."""
    p = OxmlElement("w:p")
    p_pr = OxmlElement("w:pPr")
    if page_break:
        p_pr.append(OxmlElement("w:pageBreakBefore"))
    if right is not None:
        tabs = OxmlElement("w:tabs")
        tab = OxmlElement("w:tab")
        tab.set(qn("w:val"), "right")
        tab.set(qn("w:pos"), "8640")
        tabs.append(tab)
        p_pr.append(tabs)
    spacing = OxmlElement("w:spacing")
    spacing.set(qn("w:before"), str(before))
    spacing.set(qn("w:after"), str(after))
    spacing.set(qn("w:line"), "360")
    spacing.set(qn("w:lineRule"), "auto")
    p_pr.append(spacing)
    jc = OxmlElement("w:jc")
    jc.set(qn("w:val"), align)
    p_pr.append(jc)
    p.append(p_pr)

    def run(value, tab=False):
        r = OxmlElement("w:r")
        r_pr = OxmlElement("w:rPr")
        fonts = OxmlElement("w:rFonts")
        for attr in ("ascii", "hAnsi", "cs"):
            fonts.set(qn(f"w:{attr}"), "Times New Roman")
        r_pr.append(fonts)
        if bold:
            r_pr.append(OxmlElement("w:b"))
        for tag in ("w:sz", "w:szCs"):
            sz = OxmlElement(tag)
            sz.set(qn("w:val"), str(int(size * 2)))
            r_pr.append(sz)
        r.append(r_pr)
        if tab:
            r.append(OxmlElement("w:tab"))
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = value
        r.append(t)
        p.append(r)

    run(text)
    if right is not None:
        run(right, tab=True)
    return p


def add_front_matter_pages(doc: Document) -> None:
    """SOP order: abstract, approval certificate, declaration, plagiarism
    certificate, Turnitin report, then the contents."""
    contents = U.find_paragraph(doc, "TABLE OF CONTENTS")._p
    elements = []
    for page in C.FRONT_PAGES:
        for kind, *values in page:
            if kind == "title":
                elements.append(front_paragraph(values[0], size=16, bold=True, align="center", page_break=True, before=480, after=480))
            elif kind == "heading":
                elements.append(front_paragraph(values[0], size=14, bold=True, align="center", before=240, after=240))
            elif kind == "right":
                elements.append(front_paragraph(values[0], align="right", after=240))
            elif kind == "line":
                elements.append(front_paragraph(values[0], align="left", after=360, right=values[1]))
            elif kind == "gap":
                elements.append(front_paragraph(after=240))
            else:
                elements.append(front_paragraph(values[0]))
    U.insert_before(contents, elements)


def roman_front_matter(doc: Document) -> None:
    """Guideline: front matter in roman numerals, the title page unnumbered."""
    sect_pr = next(doc.element.body.iter(qn("w:sectPr")))
    assert sect_pr.getparent().tag == qn("w:pPr"), "Expected the front matter to end in a section break"
    pg = sect_pr.find(qn("w:pgNumType"))
    pg.set(qn("w:fmt"), "lowerRoman")
    if sect_pr.find(qn("w:titlePg")) is None:
        later = [qn(t) for t in ("w:textDirection", "w:bidi", "w:rtlGutter", "w:docGrid", "w:printerSettings", "w:sectPrChange")]
        title_pg = OxmlElement("w:titlePg")
        following = next((c for c in sect_pr if c.tag in later), None)
        if following is not None:
            following.addprevious(title_pg)
        else:
            sect_pr.append(title_pg)


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
    extend_chapter_3(doc, templates)
    replace_chapter_body(doc, "4.1 Development Environment", render_blocks(doc, templates, without_moved_tables(C.CHAPTER_4)))
    replace_chapter_body(doc, "5.1 Testing Approach", render_blocks(doc, templates, without_moved_tables(C.CHAPTER_5)))
    replace_chapter_body(doc, "6.1 Conclusion", render_blocks(doc, templates, C.CHAPTER_6))
    add_appendices(doc, templates)
    renumber_tables(doc)
    edit_abbreviations(doc)
    edit_references(doc)
    U.normalize_typography(doc)
    for element in abstract:
        for run in element.iter(qn("w:r")):
            from docx.text.run import Run

            U.set_run_font(Run(run, None), size=12)
    chapter_title_pages(doc)
    appendix_title_pages(doc)
    add_front_matter_pages(doc)
    roman_front_matter(doc)
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
