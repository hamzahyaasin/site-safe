"""Editable copies of the matplotlib figures.

``save_drawio`` walks a drawn axes and writes every box, ellipse, diamond,
line, arrow and label as a draw.io cell, so a figure can be changed in
diagrams.net (free, desktop or app.diagrams.net) without the script. Text
sits inside the shape that contains it and arrows that end on a shape's
border are attached to it, so moving a box carries its text and arrows.
``save_svg`` writes the same figure as SVG with live text for Figma,
Inkscape or Illustrator.

The PNGs in docs/figures stay the copies the report uses; an edited
.drawio file has to be exported to PNG again by hand (File > Export as >
PNG, 220 dpi) and then replaces the PNG of the same name.
"""

from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
from matplotlib.colors import to_hex
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle
from matplotlib.text import Annotation

PX = 96  # draw.io pixels per inch
TOL = 0.035  # inches: an arrow end this close to a border is attached to the shape


def _hex(color) -> str:
    return "none" if color is None or (len(color) == 4 and color[3] == 0) else to_hex(color, keep_alpha=False)


def _dashed(linestyle) -> bool:
    if isinstance(linestyle, tuple):
        return bool(linestyle[1])
    return linestyle not in ("-", "solid", None)


def _style(**items) -> str:
    return "".join(f"{k}={v};" for k, v in items.items() if v is not None)


class _Shape:
    def __init__(self, cid, kind, x, y, w, h):
        self.id, self.kind, self.x, self.y, self.w, self.h = cid, kind, x, y, w, h

    @property
    def area(self):
        return self.w * self.h

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def border_point(self, px, py):
        """(exitX, exitY) when the point lies on this shape's border, else None."""
        rx, ry = self.w / 2, self.h / 2
        cx, cy = self.x + rx, self.y + ry
        if self.kind == "ellipse":
            if rx <= 0 or ry <= 0:
                return None
            r = math.hypot((px - cx) / rx, (py - cy) / ry)
            if abs(r - 1) * min(rx, ry) > TOL:
                return None
        elif self.kind == "rhombus":
            r = abs(px - cx) / rx + abs(py - cy) / ry
            if abs(r - 1) * min(rx, ry) > TOL:
                return None
        else:
            inside = self.x - TOL <= px <= self.x + self.w + TOL and self.y - TOL <= py <= self.y + self.h + TOL
            deep = self.x + TOL < px < self.x + self.w - TOL and self.y + TOL < py < self.y + self.h - TOL
            if not inside or deep:
                return None
        return (min(max((px - self.x) / self.w, 0), 1), min(max((py - self.y) / self.h, 0), 1))


class _Writer:
    def __init__(self, name):
        self.file = ET.Element("mxfile", host="make_figures.py")
        diagram = ET.SubElement(self.file, "diagram", name=name, id=name)
        model = ET.SubElement(diagram, "mxGraphModel", grid="0", page="0", math="0", shadow="0")
        self.root = ET.SubElement(model, "root")
        ET.SubElement(self.root, "mxCell", id="0")
        ET.SubElement(self.root, "mxCell", id="1", parent="0")
        self.next_id = 2
        self.shapes: list[_Shape] = []

    def _id(self):
        self.next_id += 1
        return f"c{self.next_id}"

    def vertex(self, kind, x, y, w, h, style, value="", parent=None):
        cid = self._id()
        px, py = x, y
        if parent is not None:
            px, py = x - parent.x, y - parent.y
        cell = ET.SubElement(self.root, "mxCell", id=cid, value=value, style=style, vertex="1",
                             parent=parent.id if parent is not None else "1")
        ET.SubElement(cell, "mxGeometry", x=f"{px * PX:.1f}", y=f"{py * PX:.1f}", width=f"{w * PX:.1f}",
                      height=f"{h * PX:.1f}", **{"as": "geometry"})
        if kind != "text":
            self.shapes.append(_Shape(cid, kind, x, y, w, h))
        return cid

    def _attach(self, point):
        hits = [(s, s.border_point(*point)) for s in self.shapes]
        hits = [(s, p) for s, p in hits if p is not None]
        if not hits:
            return None, None
        shape, rel = min(hits, key=lambda hit: hit[0].area)
        return shape, rel

    def edge(self, points, stroke, width, dashed, start_arrow, end_arrow):
        style = dict(html="1", rounded="0", endArrow="block" if end_arrow else "none", endFill="1",
                     startArrow="block" if start_arrow else "none", startFill="1", endSize="5", startSize="5",
                     strokeColor=stroke, strokeWidth=f"{width:.2f}", dashed="1" if dashed else "0")
        attrs = {}
        source, src_rel = self._attach(points[0])
        target, tgt_rel = self._attach(points[-1])
        if source is not None and source is not target:
            attrs["source"] = source.id
            style.update(exitX=f"{src_rel[0]:.3f}", exitY=f"{src_rel[1]:.3f}", exitDx="0", exitDy="0", exitPerimeter="0")
        if target is not None and source is not target:
            attrs["target"] = target.id
            style.update(entryX=f"{tgt_rel[0]:.3f}", entryY=f"{tgt_rel[1]:.3f}", entryDx="0", entryDy="0", entryPerimeter="0")
        if len(points) > 2:
            style["edgeStyle"] = "none"
        cell = ET.SubElement(self.root, "mxCell", id=self._id(), value="", style=_style(**style), edge="1", parent="1", **attrs)
        geometry = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        ET.SubElement(geometry, "mxPoint", x=f"{points[0][0] * PX:.1f}", y=f"{points[0][1] * PX:.1f}", **{"as": "sourcePoint"})
        ET.SubElement(geometry, "mxPoint", x=f"{points[-1][0] * PX:.1f}", y=f"{points[-1][1] * PX:.1f}", **{"as": "targetPoint"})
        if len(points) > 2:
            array = ET.SubElement(geometry, "Array", **{"as": "points"})
            for x, y in points[1:-1]:
                ET.SubElement(array, "mxPoint", x=f"{x * PX:.1f}", y=f"{y * PX:.1f}")

    def save(self, path: Path):
        ET.indent(self.file)
        ET.ElementTree(self.file).write(path, encoding="utf-8", xml_declaration=False)


def _shape_style(patch, kind):
    fill = _hex(patch.get_facecolor())
    style = dict(html="1", whiteSpace="wrap", fillColor=fill, strokeColor=_hex(patch.get_edgecolor()),
                 strokeWidth=f"{patch.get_linewidth() * 96 / 72:.2f}", dashed="1" if _dashed(patch.get_linestyle()) else "0")
    if kind == "rounded":
        style.update(rounded="1", arcSize="12", absoluteArcSize="0")
    elif kind == "ellipse":
        style = {"ellipse": None, **style}
    elif kind == "rhombus":
        style = {"rhombus": None, **style}
    text = "".join(f"{k};" if v is None else f"{k}={v};" for k, v in style.items())
    return text


def save_drawio(fig, ax, path: Path) -> None:
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    to_data = ax.transData.inverted()
    writer = _Writer(path.stem)

    artists = sorted(list(ax.patches) + list(ax.lines) + list(ax.texts), key=lambda a: a.get_zorder())
    texts = []
    for artist in artists:
        if isinstance(artist, Annotation):
            if artist.arrow_patch is not None:
                (x0, y0), (x1, y1) = artist.xyann, artist.xy
                props = artist.arrowprops or {}
                writer.edge([(x0, y0), (x1, y1)], _hex(props.get("color", "#000000")), props.get("lw", 0.8) * 96 / 72,
                            False, False, True)
            if artist.get_text():
                texts.append(artist)
        elif isinstance(artist, matplotlib.text.Text):
            if artist.get_text() and artist.get_visible():
                texts.append(artist)
        elif isinstance(artist, FancyArrowPatch):
            (x0, y0), (x1, y1) = artist._posA_posB
            style = type(artist.get_arrowstyle()).__name__
            writer.edge([(x0, y0), (x1, y1)], _hex(artist.get_edgecolor()), artist.get_linewidth() * 96 / 72,
                        _dashed(artist.get_linestyle()), style.endswith(("A", "AB")), style.endswith("B"))
        elif isinstance(artist, FancyBboxPatch):
            writer.vertex("rect", artist.get_x(), artist.get_y(), artist.get_width(), artist.get_height(),
                          _shape_style(artist, "rounded"))
        elif isinstance(artist, Circle):
            (cx, cy), r = artist.center, artist.radius
            writer.vertex("ellipse", cx - r, cy - r, 2 * r, 2 * r, _shape_style(artist, "ellipse"))
        elif isinstance(artist, Ellipse):
            (cx, cy), w, h = artist.center, artist.width, artist.height
            writer.vertex("ellipse", cx - w / 2, cy - h / 2, w, h, _shape_style(artist, "ellipse"))
        elif isinstance(artist, Rectangle):
            writer.vertex("rect", artist.get_x(), artist.get_y(), artist.get_width(), artist.get_height(),
                          _shape_style(artist, "rect"))
        elif isinstance(artist, Polygon):
            xy = artist.get_xy()[:4]
            xs, ys = xy[:, 0], xy[:, 1]
            writer.vertex("rhombus", xs.min(), ys.min(), xs.max() - xs.min(), ys.max() - ys.min(), _shape_style(artist, "rhombus"))
        elif isinstance(artist, Line2D):
            points = list(zip(artist.get_xdata(), artist.get_ydata()))
            if len(points) >= 2:
                writer.edge(points, _hex(artist.get_color()), artist.get_linewidth() * 96 / 72,
                            _dashed(artist.get_linestyle()), False, False)

    for text in texts:
        extent = text.get_window_extent(renderer)
        (x0, y1), (x1, y0) = to_data.transform([(extent.x0, extent.y0), (extent.x1, extent.y1)])
        x0, x1 = min(x0, x1), max(x0, x1)
        y0, y1 = min(y0, y1), max(y0, y1)
        pad = 0.02
        x0, x1, y0, y1 = x0 - pad, x1 + pad, y0 - pad / 2, y1 + pad / 2
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        holders = [s for s in writer.shapes if s.contains(cx, cy) and s.kind != "text"]
        parent = min(holders, key=lambda s: s.area) if holders else None
        weight = text.get_fontweight()
        bold = weight == "bold" or (isinstance(weight, int) and weight >= 600)
        font_style = (1 if bold else 0) | (2 if text.get_fontstyle() == "italic" else 0)
        bbox = text.get_bbox_patch()
        style = dict(text=None, html="0", whiteSpace="nowrap", align={"center": "center", "right": "right"}.get(text.get_ha(), "left"),
                     verticalAlign="middle", fontFamily="Arial", fontSize=f"{text.get_fontsize() * 96 / 72:.1f}",
                     fontColor=_hex(text.get_color()), fontStyle=str(font_style), strokeColor="none", fillColor="none",
                     spacing="0", labelBackgroundColor=_hex(bbox.get_facecolor()) if bbox is not None else None)
        style_text = "".join(f"{k};" if v is None else f"{k}={v};" for k, v in style.items() if v is not None or k == "text")
        writer.vertex("text", x0, y0, x1 - x0, y1 - y0, style_text, value=text.get_text(), parent=parent)
    writer.save(path)


def save_svg(fig, path: Path) -> None:
    with matplotlib.rc_context({"svg.fonttype": "none"}):
        fig.savefig(path, format="svg", bbox_inches="tight", pad_inches=0.04)
