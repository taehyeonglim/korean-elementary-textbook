#!/usr/bin/env python3
"""Render deterministic problem and answer pages from workbook JSON.

The workbook JSON is the only content source. This script writes inspectable SVG
sources, rasterizes them into 1024x1536 PNG/WebP assets, and makes four-page
PDFs using the preserved GPT-generated covers plus the deterministic pages.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from diagram_registry import diagram_spec, load_registry, render as render_registry

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
PUBLIC = ROOT / "public"
SVG_ROOT = ROOT / "artifacts" / "worksheet-svg"
THEME_PATH = ROOT / "config" / "worksheet-theme.json"
CATALOG_PATH = CONTENT / "catalog.json"
COVER_REGISTRY_PATH = ROOT / "config" / "cover-masters.json"
REGISTRY: dict[str, Any] = {}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def svg_text(text: str, x: float, y: float, size: float, color: str, *, weight: int = 400, anchor: str = "start", attrs: str = "") -> str:
    return f'<text x="{x}" y="{y}" font-family="{THEME["type"]["fontFamily"]}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}" {attrs}>{esc(text)}</text>'


def wrap_korean(text: str, limit: int) -> list[str]:
    """A predictable character-width wrapper suitable for the fixed worksheet grid."""
    text = " ".join(text.split())
    lines: list[str] = []
    while len(text) > limit:
        split = text.rfind(" ", 0, limit + 1)
        if split < max(4, limit // 2):
            split = limit
        lines.append(text[:split].strip())
        text = text[split:].strip()
    if text:
        lines.append(text)
    return lines


def paragraph(text: str, x: float, y: float, size: float, color: str, max_chars: int, line_height: float, *, weight: int = 400) -> str:
    lines = wrap_korean(text, max_chars)
    spans = "".join(f'<tspan x="{x}" dy="{0 if i == 0 else line_height}">{esc(line)}</tspan>' for i, line in enumerate(lines))
    return f'<text x="{x}" y="{y}" font-family="{THEME["type"]["fontFamily"]}" font-size="{size}" font-weight="{weight}" fill="{color}">{spans}</text>'


def level_label(level: str) -> str:
    return {"foundation": "기초 다지기", "standard": "기본 완성", "challenge": "도전 확장"}[level]


def level_color(level: str) -> str:
    return THEME["colors"][level]


GEOMETRY_MARKERS = {
    "two-digit-addition-subtraction": ["blank-place-value-grid", "blank-place-value-grid", "blank-place-value-grid", "blank-place-value-grid", "blank-place-value-grid", "blank-place-value-grid"],
    "fractions": ["cells=8;filled=3", "cards=3;fractions=1/5,3/5,5/3", "bars=2;cells=4+4;filled=4+3", "bars=2;cells=7+7;filled=3+5", "equal-circles=2;sectors=3+5", "cards=4;empty-zones=1"],
    "angles": ["unit=degree", "rays=2;angle=60", "right-angle=90;bisector=45", "triangle-angles=50,60,70", "quadrilateral=generic;not-to-scale", "triples=40,65,75|40,65,80"],
    "plane-shapes": ["selectors=circle,triangle,rectangle", "selectors=circle,triangle,rectangle", "triangle;vertices=3", "quadrilateral;sides=4", "house=triangle1,rectangle1,circle1", "equilateral-triangles=2;shared-side=1;exterior=4"],
    "ratios-and-rates": ["red=6;yellow=4", "grid=20;filled=8", "conversion-boxes=3;empty=3", "conversion-boxes=3;empty=3", "grid=25;filled=0", "bars=18/24,21/30;fills=.75,.70;percent-labels=0"],
    "circle-pi-area": ["circle;diameter=10", "circle;radius=4", "circle;circumference=62.8;diameter=unknown", "circle;diameter=12", "circle;radius=5;loops=3", "square-side=14;inscribed-circle=1"],
}


def legacy_diagram(workbook_id: str, question_index: int, x: int, y: int) -> str:
    """Draw source-derived math aids from explicit geometry and numeric counts."""
    stroke = THEME["colors"]["brand"]
    accent = THEME["colors"]["accent"]
    muted = THEME["colors"]["muted"]
    if workbook_id == "fractions":
        def bar(total: int, filled: int, bx: int, by: int, label: str = "") -> str:
            cell = 200 / total
            cells = "".join(f'<rect x="{bx + cell * i:.2f}" y="{by}" width="{cell:.2f}" height="42" fill="{accent if i < filled else "#FFFFFF"}" stroke="{stroke}" stroke-width="3"/>' for i in range(total))
            return cells + (svg_text(label, bx + 100, by + 72, 17, muted, weight=700, anchor="middle") if label else "")
        if question_index == 0: return bar(8, 3, x, y + 36)
        if question_index == 1:
            return "".join(f'<rect x="{x + n * 70}" y="{y + 22}" width="60" height="62" rx="10" fill="#FFFFFF" stroke="{stroke}" stroke-width="3"/>{svg_text(label, x + 30 + n * 70, y + 61, 18, muted, weight=700, anchor="middle")}' for n, label in enumerate(("1/5", "3/5", "5/3")))
        if question_index == 2: return bar(4, 4, x, y + 10) + bar(4, 3, x, y + 85)
        if question_index == 3: return bar(7, 3, x, y + 18, "3/7") + bar(7, 5, x, y + 98, "5/7")
        if question_index == 4:
            def pie(parts: int, bx: int) -> str:
                wedges = []
                cx, cy, r = bx + 52, y + 78, 46
                for part in range(parts):
                    a0, a1 = -math.pi / 2 + 2 * math.pi * part / parts, -math.pi / 2 + 2 * math.pi * (part + 1) / parts
                    wedges.append(f'<path d="M {cx} {cy} L {cx+r*math.cos(a0):.1f} {cy+r*math.sin(a0):.1f} A {r} {r} 0 0 1 {cx+r*math.cos(a1):.1f} {cy+r*math.sin(a1):.1f} Z" fill="#FFFFFF" stroke="{stroke}" stroke-width="2"/>')
                return "".join(wedges)
            return pie(3, x) + pie(5, x + 116)
        return "".join(f'<rect x="{x + n*52}" y="{y+32}" width="42" height="62" rx="6" fill="#FFFFFF" stroke="{stroke}" stroke-width="3"/>{svg_text(label, x+n*52+21, y+70, 15, muted, weight=700, anchor="middle")}' for n, label in enumerate(("1/4", "4/3", "3/3", "1½")))
    if workbook_id == "angles":
        if question_index == 0: return svg_text("각도의 단위: ___", x + 100, y + 85, 24, stroke, weight=800, anchor="middle")
        if question_index in (1, 2):
            degrees = 60 if question_index == 1 else 90
            cx, cy, r = x + 98, y + 142, 108
            end_a = -math.radians(degrees)
            rays = f'<path d="M {cx} {cy} L {cx+r} {cy} M {cx} {cy} L {cx+r*math.cos(end_a):.1f} {cy+r*math.sin(end_a):.1f}" stroke="{stroke}" stroke-width="7" stroke-linecap="round" fill="none"/>'
            arc = f'<path d="M {cx+38} {cy} A 38 38 0 0 0 {cx+38*math.cos(end_a):.1f} {cy+38*math.sin(end_a):.1f}" stroke="{accent}" stroke-width="5" fill="none"/>'
            if question_index == 2:
                bisector = -math.pi / 4
                rays += f'<path d="M {cx} {cy} L {cx+84*math.cos(bisector):.1f} {cy+84*math.sin(bisector):.1f}" stroke="{accent}" stroke-width="4" stroke-dasharray="7 6"/>'
            return rays + arc + svg_text(f"{degrees}°", cx + 56, cy - 28, 19, muted, weight=700)
        if question_index == 3:
            # 50°/60° rays meet at a calculated apex; the derived 70° stays unknown.
            a, b = (x + 20, y + 158), (x + 195, y + 158)
            tan_left, tan_right = math.tan(math.radians(50)), math.tan(math.radians(60))
            apex_x = (tan_right * b[0] + tan_left * a[0]) / (tan_left + tan_right)
            c = (apex_x, a[1] - tan_left * (apex_x - a[0]))
            return f'<polygon points="{a[0]},{a[1]} {b[0]},{b[1]} {c[0]},{c[1]}" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/>' + svg_text("50°", a[0]+25, a[1]-16, 17, muted, weight=700) + svg_text("60°", b[0]-25, b[1]-16, 17, muted, weight=700, anchor="end") + svg_text("?", c[0], c[1]+42, 22, accent, weight=800, anchor="middle")
        if question_index == 4: return f'<polygon points="{x+32},{y+142} {x+84},{y+25} {x+182},{y+42} {x+202},{y+148}" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/>' + svg_text("그림은 정확한 크기가 아님", x+110, y+186, 14, muted, anchor="middle")
        return svg_text("가: 40° · 65° · 75°", x, y+58, 18, muted, weight=700) + svg_text("나: 40° · 65° · 80°", x, y+112, 18, muted, weight=700)
    if workbook_id == "circle-pi-area":
        if question_index in (0, 3):
            d = 10 if question_index == 0 else 12; r = 70; cx, cy = x + 105, y + 88
            return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/><line x1="{cx-r}" y1="{cy}" x2="{cx+r}" y2="{cy}" stroke="{accent}" stroke-width="5"/>' + svg_text(f"d = {d}cm", cx, cy+118, 18, muted, weight=700, anchor="middle")
        if question_index == 1:
            cx, cy, r = x+105, y+88, 64
            return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/><line x1="{cx}" y1="{cy}" x2="{cx+r}" y2="{cy}" stroke="{accent}" stroke-width="5"/>' + svg_text("r = 4cm", cx+34, cy-14, 18, muted, weight=700)
        if question_index == 2: return f'<circle cx="{x+105}" cy="{y+82}" r="62" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/>' + svg_text("원주 = 62.8cm", x+105, y+174, 18, muted, weight=700, anchor="middle") + svg_text("d = ?", x+105, y+204, 18, accent, weight=800, anchor="middle")
        if question_index == 4:
            cx, cy, r = x+105, y+86, 57
            return f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{stroke}" stroke-width="5"/><circle cx="{cx}" cy="{cy}" r="{r+13}" fill="none" stroke="{accent}" stroke-width="4" stroke-dasharray="9 7"/><path d="M {cx+r+18} {cy} q 26 -20 0 -42" fill="none" stroke="{accent}" stroke-width="4"/>' + svg_text("3바퀴", x+105, y+190, 18, muted, weight=700, anchor="middle")
        return f'<rect x="{x+28}" y="{y+10}" width="156" height="156" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/><circle cx="{x+106}" cy="{y+88}" r="78" fill="#FFFFFF" stroke="{accent}" stroke-width="5"/>' + svg_text("한 변 14cm", x+106, y+198, 18, muted, weight=700, anchor="middle")
    if workbook_id == "plane-shapes":
        if question_index in (0, 1):
            return f'<circle cx="{x+34}" cy="{y+80}" r="28" fill="#EAF2FB" stroke="{stroke}" stroke-width="4"/>{svg_text("가",x+34,y+132,16,muted,weight=700,anchor="middle")}<polygon points="{x+86},{y+108} {x+118},{y+46} {x+150},{y+108}" fill="#FFFFFF" stroke="{stroke}" stroke-width="4"/>{svg_text("나",x+118,y+132,16,muted,weight=700,anchor="middle")}<rect x="{x+166}" y="{y+50}" width="52" height="52" fill="#FFFFFF" stroke="{stroke}" stroke-width="4"/>{svg_text("다",x+192,y+132,16,muted,weight=700,anchor="middle")}'
        if question_index == 2: return f'<polygon points="{x+28},{y+144} {x+105},{y+25} {x+184},{y+144}" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/>' + "".join(f'<circle cx="{px}" cy="{py}" r="6" fill="{accent}"/>' for px, py in ((x+28,y+144),(x+105,y+25),(x+184,y+144))) + svg_text("꼭짓점", x+105, y+184, 18, muted, weight=700, anchor="middle")
        if question_index == 3:
            return f'<rect x="{x+18}" y="{y+42}" width="72" height="72" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/><polygon points="{x+122},{y+42} {x+202},{y+58} {x+184},{y+122} {x+106},{y+106}" fill="#FFFFFF" stroke="{stroke}" stroke-width="5"/>' + svg_text("여러 사각형", x+110, y+172, 19, muted, weight=700, anchor="middle")
        if question_index == 4: return f'<polygon points="{x+30},{y+80} {x+104},{y+18} {x+178},{y+80}" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/><rect x="{x+54}" y="{y+80}" width="100" height="80" fill="#FFFFFF" stroke="{stroke}" stroke-width="5"/><circle cx="{x+104}" cy="{y+120}" r="18" fill="{accent}"/>'
        return f'<polygon points="{x+52},{y+113} {x+157},{y+113} {x+104.5},{y+22}" fill="#EAF2FB" stroke="{stroke}" stroke-width="5"/><polygon points="{x+52},{y+113} {x+157},{y+113} {x+104.5},{y+204}" fill="#FFFFFF" stroke="{stroke}" stroke-width="5"/><line x1="{x+52}" y1="{y+113}" x2="{x+157}" y2="{y+113}" stroke="{accent}" stroke-width="5"/>' + svg_text("바깥쪽 변 ___개", x+105, y+231, 18, muted, weight=700, anchor="middle")
    if workbook_id == "ratios-and-rates":
        if question_index == 0:
            return "".join(f'<circle cx="{x+25+n*31}" cy="{y+48}" r="12" fill="{accent}" stroke="{stroke}" stroke-width="2"/>' for n in range(6)) + "".join(f'<circle cx="{x+55+n*31}" cy="{y+96}" r="12" fill="#F8D968" stroke="{stroke}" stroke-width="2"/>' for n in range(4))
        if question_index in (1, 4):
            filled = 8 if question_index == 1 else 0
            return "".join(f'<rect x="{x+(n%5)*39}" y="{y+(n//5)*39}" width="31" height="31" fill="{accent if n < filled else "#FFFFFF"}" stroke="{stroke}" stroke-width="2"/>' for n in range(20 if question_index == 1 else 25))
        if question_index in (2, 3): return "".join(f'<rect x="{x+n*72}" y="{y+55}" width="62" height="56" rx="8" fill="#FFFFFF" stroke="{stroke}" stroke-width="3"/>' for n in range(3))
        return f'<rect x="{x}" y="{y+36}" width="200" height="28" fill="#FFFFFF" stroke="{stroke}" stroke-width="3"/><rect x="{x}" y="{y+36}" width="150" height="28" fill="{accent}"/>{svg_text("18/24",x+100,y+25,17,muted,weight=700,anchor="middle")}<rect x="{x}" y="{y+118}" width="200" height="28" fill="#FFFFFF" stroke="{stroke}" stroke-width="3"/><rect x="{x}" y="{y+118}" width="140" height="28" fill="{accent}"/>{svg_text("21/30",x+100,y+107,17,muted,weight=700,anchor="middle")}'
    # Two-digit addition/subtraction intentionally gives no numeric hint: blank place-value grid and working area only.
    grid = "".join(f'<rect x="{x + col * 58}" y="{y + row * 44}" width="58" height="44" fill="#FFFFFF" stroke="{stroke}" stroke-width="2"/>' for row in range(3) for col in range(3))
    lines = "".join(f'<line x1="{x+8}" y1="{y+164+line*22}" x2="{x+196}" y2="{y+164+line*22}" stroke="{muted}" stroke-width="2"/>' for line in range(2))
    return grid + lines + svg_text("계산 과정을 써 보세요", x + 104, y + 218, 17, muted, weight=700, anchor="middle")


def resolved_spec(workbook: dict[str, Any], question: dict[str, Any]) -> dict[str, Any] | None:
    return diagram_spec(REGISTRY, workbook["id"], question["id"])


def diagram(workbook: dict[str, Any], question: dict[str, Any], question_index: int, x: int, y: int) -> str:
    spec = resolved_spec(workbook, question)
    if spec is not None:
        return render_registry(spec, x, y, THEME)
    if workbook["id"] in GEOMETRY_MARKERS:
        return legacy_diagram(workbook["id"], question_index, x, y)
    # A new module without a Sol registry entry can be rendered privately for
    # author review, but uses no inferred mathematical result.
    return render_registry(REGISTRY["defaults"], x, y, THEME)


def geometry_marker(workbook: dict[str, Any], question: dict[str, Any], question_index: int) -> str:
    spec = resolved_spec(workbook, question)
    if spec is not None:
        return spec.get("geometry", spec.get("type", spec.get("kind", "student-workspace")))
    return GEOMETRY_MARKERS.get(workbook["id"], ["student-workspace"] * 6)[question_index]


def page_shell(workbook: dict[str, Any], page_number: int, label: str) -> list[str]:
    c = THEME["colors"]
    width = THEME["canvas"]["width"]
    margin = THEME["canvas"]["margin"]
    header_height = THEME["layout"]["headerHeight"]
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (f'<svg xmlns="http://www.w3.org/2000/svg" width="{THEME["canvas"]["physicalWidthMm"]}mm" '
         f'height="{THEME["canvas"]["physicalHeightMm"]}mm" viewBox="0 0 {THEME["canvas"]["outputWidth"]} {THEME["canvas"]["outputHeight"]}" role="img">'),
        f'<rect width="100%" height="100%" fill="{c["paper"]}"/>',
        (f'<g transform="scale({THEME["canvas"]["outputWidth"] / width:.8f} '
         f'{THEME["canvas"]["outputHeight"] / THEME["canvas"]["height"]:.8f})">'),
        f'<rect width="100%" height="{header_height}" fill="{c["brand"]}"/>',
        svg_text("초등 수학 한 장", margin, 58, 22, "#FFFFFF", weight=700),
        svg_text(workbook["module"], margin, 112, THEME["type"]["title"], "#FFFFFF", weight=800),
        svg_text(f'{workbook["gradeBand"]}학년군 · {label}' + (" · 원주율은 3.14로 계산하세요." if workbook["id"] == "circle-pi-area" and label == "문제" else ""), margin, 152, 18 if workbook["id"] == "circle-pi-area" and label == "문제" else THEME["type"]["subtitle"], "#FFFFFF"),
        svg_text(str(page_number), width - margin, 152, 22, "#FFFFFF", weight=700, anchor="end"),
    ]


def footer(parts: list[str]) -> None:
    c = THEME["colors"]
    width, height, margin = THEME["canvas"]["width"], THEME["canvas"]["height"], THEME["canvas"]["margin"]
    parts.append(f'<line x1="{margin}" y1="{height - 76}" x2="{width - margin}" y2="{height - 76}" stroke="{c["line"]}" stroke-width="2"/>')
    parts.append(svg_text("Taehyeong Lim · CC BY-NC-SA 4.0", margin, height - 42, 16, c["muted"], weight=600))
    parts.append(svg_text("이미지 제작: Gongnyang Prompt Kit", width - margin, height - 62, 15, c["muted"], anchor="end"))
    parts.append(svg_text("문항·해설은 학습지 JSON에서 결정론적으로 생성됨", width - margin, height - 35, 15, c["muted"], anchor="end"))
    parts.append("</g></svg>")


def cover_svg(workbook: dict[str, Any], master: Path) -> str:
    """Compose approved text-free masters with only JSON-derived metadata."""
    c, canvas_config = THEME["colors"], THEME["canvas"]
    source_data = base64.b64encode(master.read_bytes()).decode("ascii")
    title_lines = wrap_korean(workbook["module"], 11)[:2]
    if len(title_lines) > 2:
        raise ValueError(f'{workbook["id"]}: cover title exceeds two lines')
    width, height = canvas_config["width"], canvas_config["height"]
    sx, sy = canvas_config["outputWidth"] / width, canvas_config["outputHeight"] / height
    standards = " ".join(workbook["standardCodes"])
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas_config["physicalWidthMm"]}mm" height="{canvas_config["physicalHeightMm"]}mm" viewBox="0 0 {canvas_config["outputWidth"]} {canvas_config["outputHeight"]}" role="img">',
        f'<image href="data:image/png;base64,{source_data}" x="0" y="0" width="{canvas_config["outputWidth"]}" height="{canvas_config["outputHeight"]}" preserveAspectRatio="xMidYMid slice"/>',
        f'<g transform="scale({sx:.8f} {sy:.8f})">',
        f'<rect x="72" y="72" width="880" height="118" rx="20" fill="{c["paper"]}" opacity=".95"/>',
        svg_text("초등 수학 한 장", 104, 125, 28, c["brand"], weight=800),
        svg_text(f'{workbook["gradeBand"]}학년군 · {workbook["domain"]}', 104, 166, 20, c["muted"], weight=700),
        f'<rect x="72" y="892" width="880" height="300" rx="20" fill="{c["paper"]}" opacity=".95"/>',
    ]
    for index, line in enumerate(title_lines):
        parts.append(svg_text(line, 104, 968 + index * 70, 54 if len(title_lines) == 1 else 46, c["brand"], weight=800))
    parts.extend([
        paragraph(standards, 104, 1138, 18, c["muted"], 56, 26, weight=700),
        f'<rect x="72" y="1230" width="880" height="110" rx="20" fill="{c["paper"]}" opacity=".95"/>',
        svg_text("기초", 240, 1298, 21, c["brand"], weight=800, anchor="middle"),
        svg_text("표준", 512, 1298, 21, c["brand"], weight=800, anchor="middle"),
        svg_text("도전", 784, 1298, 21, c["brand"], weight=800, anchor="middle"),
        f'<rect x="72" y="1370" width="880" height="110" rx="20" fill="{c["paper"]}" opacity=".95"/>',
        svg_text("Taehyeong Lim · CC BY-NC-SA 4.0", 104, 1412, 15, c["brand"], weight=700),
        svg_text("이미지 제작에 공냥 프롬프트 킷을 사용했습니다.", 104, 1450, 15, c["brand"], weight=700),
        "</g></svg>",
    ])
    return "\n".join(parts)


def cover_master(workbook: dict[str, Any], registry: dict[str, Any]) -> Path:
    domain_slug = registry.get("domainSlugs", {}).get(workbook["domain"])
    if not domain_slug:
        raise ValueError(f'{workbook["id"]}: no cover domain slug configured for {workbook["domain"]!r}')
    expected = ROOT / "assets" / "cover-masters" / f'{workbook["gradeBand"]}-{domain_slug}.png'
    match = next((item for item in registry.get("masters", []) if item.get("gradeBand") == workbook["gradeBand"] and item.get("domainSlug") == domain_slug and item.get("approved")), None)
    if not match:
        raise ValueError(f'{workbook["id"]}: no approved cover master registry entry for {workbook["gradeBand"]}/{domain_slug}')
    if match.get("masterPath"):
        expected = ROOT / match["masterPath"]
    if not expected.exists():
        raise ValueError(f'{workbook["id"]}: approved cover master missing: {expected.relative_to(ROOT)}')
    prompt = ROOT / match["promptPath"]
    if not prompt.exists() or sha256(prompt) != match.get("promptSha256"):
        raise ValueError(f'{workbook["id"]}: cover master prompt hash does not match the approved registry')
    if sha256(expected) != match.get("imageSha256"):
        raise ValueError(f'{workbook["id"]}: cover master image hash does not match the approved registry')
    with Image.open(expected) as image:
        if image.size != (1024, 1536):
            raise ValueError(f'{workbook["id"]}: cover master must be 1024x1536, got {image.size}')
    return expected


def problem_page(workbook: dict[str, Any], page_number: int, questions: list[dict[str, Any]], start_index: int) -> str:
    c = THEME["colors"]
    m = THEME["canvas"]["margin"]
    parts = page_shell(workbook, page_number, "문제")
    card_height = THEME["layout"]["problemCardHeight"]
    gap = THEME["layout"]["cardGap"]
    radius = THEME["layout"]["cardRadius"]
    for index, question in enumerate(questions):
        y = 213 + index * (card_height + gap)
        level = question["level"]
        parts.append(f'<rect x="{m}" y="{y}" width="{THEME["canvas"]["width"] - 2*m}" height="{card_height}" rx="{radius}" fill="#FFFFFF" stroke="{c["line"]}" stroke-width="2"/>')
        parts.append(f'<rect x="{m}" y="{y}" width="14" height="{card_height}" rx="7" fill="{level_color(level)}"/>')
        parts.append(f'<rect x="{m + 30}" y="{y + 24}" width="128" height="36" rx="18" fill="{level_color(level)}"/>')
        parts.append(svg_text(level_label(level), m + 94, y + 49, 17, c["ink"], weight=700, anchor="middle"))
        parts.append(svg_text(f"{start_index + index + 1}.", m + 30, y + 106, 32, c["brand"], weight=800))
        parts.append(paragraph(question["prompt"], m + 84, y + 104, THEME["type"]["body"], c["ink"], 25, 37, weight=650))
        geometry = geometry_marker(workbook, question, start_index + index)
        spec = resolved_spec(workbook, question)
        kind = "legacy" if spec is None and workbook["id"] in GEOMETRY_MARKERS else (spec or REGISTRY["defaults"])["kind"]
        parts.append(f'<g id="diagram-q{start_index + index + 1}" data-role="math-diagram" data-diagram-kind="{kind}" data-geometry="{geometry}">{diagram(workbook, question, start_index + index, 724, y + 145)}</g>')
        line_y = y + 270
        for line in range(3):
            parts.append(f'<line x1="{m + 34}" y1="{line_y + line * 42}" x2="{m + 618}" y2="{line_y + line * 42}" stroke="{c["line"]}" stroke-width="2"/>')
        parts.append(svg_text(question["standardCode"], m + 34, y + card_height - 24, 16, c["muted"], weight=600))
    footer(parts)
    return "\n".join(parts)


def answer_page(workbook: dict[str, Any]) -> str:
    c = THEME["colors"]
    m = THEME["canvas"]["margin"]
    parts = page_shell(workbook, 4, "정답·해설")
    card_height = 330
    gap = 24
    radius = THEME["layout"]["cardRadius"]
    card_width = (THEME["canvas"]["width"] - 2 * m - gap) / 2
    for index, question in enumerate(workbook["questions"]):
        column, row = index % 2, index // 2
        x, y = m + column * (card_width + gap), 214 + row * (card_height + gap)
        level = question["level"]
        level_fill = level_color(level)
        parts.append(f'<rect x="{x}" y="{y}" width="{card_width}" height="{card_height}" rx="{radius}" data-answer-level="{level}" fill="{level_fill}" stroke="{c["brand"]}" stroke-width="2"/>')
        parts.append(f'<rect x="{x + card_width - 116}" y="{y + 20}" width="92" height="32" rx="16" fill="#FFFFFF" stroke="{c["brand"]}" stroke-width="1"/>')
        parts.append(svg_text(level_label(level), x + card_width - 70, y + 42, 14, c["brand"], weight=700, anchor="middle"))
        parts.append(svg_text(f"{index + 1}.", x + 24, y + 53, 29, c["brand"], weight=800))
        parts.append(svg_text("정답", x + 74, y + 40, 17, c["muted"], weight=700))
        parts.append(paragraph(question["answer"], x + 74, y + 78, THEME["type"]["answer"], c["ink"], 21, 31, weight=800))
        parts.append(svg_text("풀이", x + 24, y + 148, 17, c["muted"], weight=700))
        explanation_limit = 27 if " " not in question["explanation"] else 18
        parts.append(paragraph(question["explanation"], x + 24, y + 182, 17, c["ink"], explanation_limit, 25))
    footer(parts)
    return "\n".join(parts)


def rasterize(source: Path, png: Path, webp: Path) -> None:
    subprocess.run(["node", str(ROOT / "scripts" / "rasterize-svg.mjs"), str(source), str(png), str(webp)], cwd=ROOT, check=True)
    with Image.open(png) as image:
        if image.size != (2480, 3508):
            raise ValueError(f"{png} rasterized at {image.size}, not A4 300dpi (2480x3508)")


def build_pdf(workbook: dict[str, Any], pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(str(pdf_path), pagesize=A4, pageCompression=1)
    document.setTitle(workbook["title"])
    document.setAuthor(workbook["author"])
    document.setSubject(f'{", ".join(workbook["standardCodes"])} · {workbook["license"]}')
    document.setCreator("초등 수학 한 장 deterministic worksheet renderer")
    page_width, page_height = A4
    for page in sorted(workbook["pages"], key=lambda item: item["order"]):
        asset = PUBLIC / page["imagePath"].lstrip("/")
        image = Image.open(asset)
        width, height = image.size
        scale = min(page_width / width, page_height / height)
        draw_width, draw_height = width * scale, height * scale
        document.drawImage(ImageReader(image), (page_width - draw_width) / 2, (page_height - draw_height) / 2, draw_width, draw_height, mask="auto")
        document.showPage()
    document.save()


def sync_metadata(workbooks: list[tuple[Path, dict[str, Any]]]) -> None:
    catalog = read_json(CATALOG_PATH)
    by_id = {workbook["id"]: workbook for _, workbook in workbooks}
    for workbook_path, workbook in workbooks:
        for page in workbook["pages"]:
            page["sha256"] = sha256(PUBLIC / page["imagePath"].lstrip("/"))
        pdf_path = PUBLIC / workbook["pdf"]["path"].lstrip("/")
        if pdf_path.exists():
            workbook["pdf"]["sha256"] = sha256(pdf_path)
        workbook_path.write_text(json.dumps(workbook, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # A targeted repair may regenerate only the affected workbook pages. Keep
    # all unrelated catalog records byte-for-byte as supplied by their owners.
    catalog["workbooks"] = [by_id.get(item["id"], item) for item in catalog["workbooks"]]
    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_workbooks(selected: set[str] | None) -> list[tuple[Path, dict[str, Any]]]:
    files = sorted((CONTENT / "workbooks").glob("*.json"))
    workbooks = [(path, read_json(path)) for path in files]
    if selected:
        workbooks = [pair for pair in workbooks if pair[1]["id"] in selected]
        missing = selected - {workbook["id"] for _, workbook in workbooks}
        if missing:
            raise ValueError(f"Unknown workbook IDs: {', '.join(sorted(missing))}")
    return workbooks


def render(workbooks: list[tuple[Path, dict[str, Any]]], *, rebuild_covers: bool) -> list[str]:
    cover_registry = read_json(COVER_REGISTRY_PATH)
    incomplete: list[str] = []
    for _, workbook in workbooks:
        if len(workbook.get("questions", [])) != 6:
            raise ValueError(f'{workbook["id"]}: exactly six JSON questions are required')
        pages = {page["id"]: page for page in workbook["pages"]}
        required = {"cover", "worksheet-1", "worksheet-2", "answers"}
        if set(pages) != required:
            raise ValueError(f'{workbook["id"]}: expected page IDs {sorted(required)}')
        svg_dir = SVG_ROOT / workbook["slug"]
        svg_dir.mkdir(parents=True, exist_ok=True)
        output_dir = PUBLIC / "workbooks" / workbook["slug"]
        output_dir.mkdir(parents=True, exist_ok=True)
        page_specs = [
            ("worksheet-1", problem_page(workbook, 2, workbook["questions"][:3], 0)),
            ("worksheet-2", problem_page(workbook, 3, workbook["questions"][3:], 3)),
            ("answers", answer_page(workbook)),
        ]
        if rebuild_covers:
            cover = pages["cover"]
            source_path = svg_dir / Path(cover["imagePath"]).with_suffix(".svg").name
            png_path = PUBLIC / cover["imagePath"].lstrip("/")
            webp_path = PUBLIC / cover["thumbnailPath"].lstrip("/")
            source_path.write_text(cover_svg(workbook, cover_master(workbook, cover_registry)), encoding="utf-8")
            rasterize(source_path, png_path, webp_path)
        for page_id, source in page_specs:
            page = pages[page_id]
            source_path = svg_dir / Path(page["imagePath"]).with_suffix(".svg").name
            png_path = PUBLIC / page["imagePath"].lstrip("/")
            webp_path = PUBLIC / page["thumbnailPath"].lstrip("/")
            source_path.write_text(source, encoding="utf-8")
            rasterize(source_path, png_path, webp_path)
        cover = PUBLIC / pages["cover"]["imagePath"].lstrip("/")
        if not cover.exists():
            incomplete.append(workbook["id"])
            print(f'Rendered {workbook["id"]}: 3 deterministic pages; no approved cover so PDF/publication is blocked')
            continue
        build_pdf(workbook, PUBLIC / workbook["pdf"]["path"].lstrip("/"))
        print(f'Rendered {workbook["id"]}: 3 deterministic pages + 4-page PDF')
    return incomplete


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", action="append", help="Workbook ID to render; repeatable. Defaults to all.")
    parser.add_argument("--sync-metadata", action="store_true", help="Update generated PNG/PDF SHA-256 values in workbook JSON and catalog.")
    parser.add_argument("--rebuild-covers", action="store_true", help="Compose 01-cover from approved grade-band/domain cover masters.")
    args = parser.parse_args()
    global THEME, REGISTRY
    THEME = read_json(THEME_PATH)
    REGISTRY = load_registry()
    workbooks = load_workbooks(set(args.workbook) if args.workbook else None)
    incomplete = render(workbooks, rebuild_covers=args.rebuild_covers)
    if incomplete and any(workbook["published"] for _, workbook in workbooks if workbook["id"] in incomplete):
        raise ValueError(f"Published workbooks require approved covers before publication: {', '.join(incomplete)}")
    if args.sync_metadata:
        sync_metadata(workbooks)
        print("Synchronized generated PNG/PDF hashes into content metadata.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as error:
        print(f"Rasterization failed: {error}", file=sys.stderr)
        raise SystemExit(error.returncode)
    except Exception as error:
        print(f"Worksheet rendering failed: {error}", file=sys.stderr)
        raise SystemExit(1)
