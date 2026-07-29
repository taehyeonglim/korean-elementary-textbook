"""Data-driven deterministic SVG primitives for worksheet diagrams.

Sol-authored module entries live in config/diagram-registry.json.  Each entry
uses a `kind`, optional `params`, a human-readable `geometry` assertion, and
machine-checkable `assertions`. Missing entries deliberately render a neutral
student workspace; they never invent a numerical answer.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "diagram-registry.json"


def load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def diagram_spec(registry: dict[str, Any], workbook_id: str, question_id: str) -> dict[str, Any] | None:
    workbook = registry.get("workbooks", {}).get(workbook_id)
    if not workbook:
        return None
    instance = workbook.get("diagrams", {}).get(question_id)
    if instance is None:
        return registry.get("defaults") if workbook.get("useDefaults", False) else None
    instance = {**instance}
    diagram_type = instance.get("type", instance.get("kind"))
    definitions = registry.get("types", {})
    definition = definitions.get(diagram_type)
    if definition is None:
        raise ValueError(f"{workbook_id}/{question_id}: undeclared diagram type {diagram_type!r}")
    if workbook.get("gradeBand") and workbook["gradeBand"] not in definition.get("supportedGradeBands", []):
        raise ValueError(f"{workbook_id}/{question_id}: diagram {diagram_type!r} is not allowed for grade band {workbook['gradeBand']}")
    params = instance.get("params", {})
    allowed = set(definition.get("paramsSchema", {}).get("allowed", []))
    unknown = set(params) - allowed
    if unknown:
        raise ValueError(f"{workbook_id}/{question_id}: undeclared params for {diagram_type}: {', '.join(sorted(unknown))}")
    instance["kind"] = diagram_type
    instance.setdefault("version", definition.get("version"))
    instance.setdefault("answerExposure", "given-only")
    instance.setdefault("assertions", {"noDerivedAnswer": True})
    return instance


def esc(value: Any) -> str:
    import html
    return html.escape(str(value), quote=True)


def text(value: str, x: float, y: float, size: float, color: str, font: str, *, weight: int = 600, anchor: str = "start") -> str:
    return f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{color}" text-anchor="{anchor}">{esc(value)}</text>'


def grid(x: float, y: float, columns: int, rows: int, cell: float, stroke: str, fill: str = "#FFFFFF", filled: int = 0, accent: str = "#E87A4B") -> str:
    return "".join(
        f'<rect x="{x + (i % columns) * cell}" y="{y + (i // columns) * cell}" width="{cell}" height="{cell}" fill="{accent if i < filled else fill}" stroke="{stroke}" stroke-width="2"/>'
        for i in range(columns * rows)
    )


def render(spec: dict[str, Any], x: float, y: float, theme: dict[str, Any]) -> str:
    """Render generic primitives. Coordinates are deterministic SVG coordinates."""
    kind = spec.get("kind", "blank-workspace")
    params = spec.get("params", {})
    colors, font = theme["colors"], theme["type"]["fontFamily"]
    stroke, accent, muted = colors["brand"], colors["accent"], colors["muted"]
    if kind == "blank-workspace":
        columns, rows, cell = int(params.get("columns", 3)), int(params.get("rows", 3)), int(params.get("cell", 44))
        return grid(x, y, columns, rows, cell, stroke) + "".join(f'<line x1="{x}" y1="{y+rows*cell+22+n*24}" x2="{x+columns*cell}" y2="{y+rows*cell+22+n*24}" stroke="{muted}" stroke-width="2"/>' for n in range(int(params.get("lines", 2))))
    if kind in {"fraction-bar", "fraction-area"}:
        total, filled = int(params["total"]), int(params.get("filled", 0))
        return grid(x, y, total, 1, 200 / total, stroke, filled=filled, accent=accent)
    if kind == "decimal-grid":
        return grid(x, y, int(params.get("columns", 10)), int(params.get("rows", 10)), float(params.get("cell", 18)), stroke, filled=int(params.get("filled", 0)), accent=accent)
    if kind == "number-line":
        start, end, ticks = float(params.get("start", 0)), float(params.get("end", 10)), int(params.get("ticks", 10))
        length = float(params.get("length", 200)); segments = max(1, ticks)
        parts = [f'<line x1="{x}" y1="{y+40}" x2="{x+length}" y2="{y+40}" stroke="{stroke}" stroke-width="4"/>']
        for index in range(segments + 1):
            px = x + index * length / segments; value = start + index * (end - start) / segments
            parts.extend([f'<line x1="{px}" y1="{y+30}" x2="{px}" y2="{y+50}" stroke="{stroke}" stroke-width="3"/>', text(str(value).rstrip("0").rstrip("."), px, y+76, 15, muted, font, anchor="middle")])
        return "".join(parts)
    if kind == "analog-clock":
        cx, cy, radius = x + 100, y + 100, float(params.get("radius", 74)); hour, minute = int(params.get("hour", 0)), int(params.get("minute", 0))
        parts = [f'<circle cx="{cx}" cy="{cy}" r="{radius}" fill="#FFFFFF" stroke="{stroke}" stroke-width="4"/>']
        for tick in range(12):
            angle = math.radians(tick * 30 - 90); parts.append(f'<line x1="{cx+(radius-10)*math.cos(angle):.1f}" y1="{cy+(radius-10)*math.sin(angle):.1f}" x2="{cx+radius*math.cos(angle):.1f}" y2="{cy+radius*math.sin(angle):.1f}" stroke="{stroke}" stroke-width="2"/>')
        hour_angle, minute_angle = math.radians((hour % 12) * 30 + minute * .5 - 90), math.radians(minute * 6 - 90)
        parts.extend([f'<line x1="{cx}" y1="{cy}" x2="{cx+(radius*.52)*math.cos(hour_angle):.1f}" y2="{cy+(radius*.52)*math.sin(hour_angle):.1f}" stroke="{stroke}" stroke-width="6" stroke-linecap="round"/>', f'<line x1="{cx}" y1="{cy}" x2="{cx+(radius*.76)*math.cos(minute_angle):.1f}" y2="{cy+(radius*.76)*math.sin(minute_angle):.1f}" stroke="{accent}" stroke-width="4" stroke-linecap="round"/>'])
        return "".join(parts)
    if kind == "ruler":
        length, ticks = float(params.get("length", 200)), int(params.get("ticks", 10))
        parts = [f'<rect x="{x}" y="{y+30}" width="{length}" height="42" fill="#FFF6D8" stroke="{stroke}" stroke-width="3"/>']
        for tick in range(ticks + 1):
            px = x + tick * length / ticks; h = 30 if tick % 5 == 0 else 18
            parts.append(f'<line x1="{px}" y1="{y+30}" x2="{px}" y2="{y+30+h}" stroke="{stroke}" stroke-width="2"/>')
        return "".join(parts)
    if kind == "solid":
        # Isometric cube with deterministic visible faces.
        return f'<polygon points="{x+35},{y+66} {x+104},{y+28} {x+174},{y+66} {x+104},{y+104}" fill="#EAF2FB" stroke="{stroke}" stroke-width="4"/><polygon points="{x+35},{y+66} {x+104},{y+104} {x+104},{y+184} {x+35},{y+146}" fill="#FFFFFF" stroke="{stroke}" stroke-width="4"/><polygon points="{x+104},{y+104} {x+174},{y+66} {x+174},{y+146} {x+104},{y+184}" fill="#DDEBFA" stroke="{stroke}" stroke-width="4"/>'
    if kind == "net":
        cells = [(1,0),(0,1),(1,1),(2,1),(1,2),(1,3)]; size = 42
        return "".join(f'<rect x="{x+cx*size}" y="{y+cy*size}" width="{size}" height="{size}" fill="#EAF2FB" stroke="{stroke}" stroke-width="3"/>' for cx, cy in cells)
    if kind in {"transform-grid", "symmetry", "perimeter-area"}:
        parts = [grid(x, y, 5, 5, 34, stroke)]
        if kind == "symmetry": parts.append(f'<line x1="{x+85}" y1="{y-8}" x2="{x+85}" y2="{y+178}" stroke="{accent}" stroke-width="4" stroke-dasharray="7 6"/>')
        if kind == "transform-grid": parts.append(f'<path d="M {x+35} {y+125} L {x+125} {y+125} M {x+125} {y+125} l -14 -12 M {x+125} {y+125} l -14 12" stroke="{accent}" stroke-width="4" fill="none"/>')
        return "".join(parts)
    if kind == "volume":
        return "".join(f'<rect x="{x+(index%4)*36+(index//4%2)*12}" y="{y+(index//4)*31}" width="32" height="28" fill="#EAF2FB" stroke="{stroke}" stroke-width="2"/>' for index in range(int(params.get("cubes", 8))))
    if kind == "table":
        return grid(x, y, int(params.get("columns", 4)), int(params.get("rows", 4)), float(params.get("cell", 38)), stroke)
    if kind == "chart":
        values = [float(value) for value in params.get("values", [3, 5, 2, 4])]
        # Keep source values intact while scaling the bars to the fixed card;
        # raw values such as 24 must not intrude into the previous question.
        scale = min(22, 140 / max(max(values or [0]), 1))
        return "".join(f'<rect x="{x+i*44}" y="{y+160-v*scale:.1f}" width="28" height="{v*scale:.1f}" fill="{accent}" stroke="{stroke}" stroke-width="2"/>' for i, v in enumerate(values)) + f'<line x1="{x}" y1="{y+160}" x2="{x+205}" y2="{y+160}" stroke="{stroke}" stroke-width="3"/>'
    if kind == "probability":
        sectors = int(params.get("sectors", 4)); cx, cy, radius = x+100, y+100, 74
        return "".join(f'<path d="M {cx} {cy} L {cx+radius*math.cos(-math.pi/2+2*math.pi*i/sectors):.1f} {cy+radius*math.sin(-math.pi/2+2*math.pi*i/sectors):.1f} A {radius} {radius} 0 0 1 {cx+radius*math.cos(-math.pi/2+2*math.pi*(i+1)/sectors):.1f} {cy+radius*math.sin(-math.pi/2+2*math.pi*(i+1)/sectors):.1f} Z" fill="{accent if i == 0 else '#EAF2FB'}" stroke="{stroke}" stroke-width="2"/>' for i in range(sectors))
    return render({"kind": "blank-workspace", "params": params}, x, y, theme)
