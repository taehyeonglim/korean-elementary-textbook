#!/usr/bin/env python3
"""Golden and rejection tests for the declarative diagram primitive registry."""

from __future__ import annotations

from diagram_registry import diagram_spec, load_registry, render

THEME = {
    "colors": {"brand": "#17324D", "accent": "#D94F32", "muted": "#61778A"},
    "type": {"fontFamily": "Apple SD Gothic Neo, sans-serif"},
}

FIXTURES = {
    "blank-workspace": {"columns": 3, "rows": 3},
    "number_line": {"min": 0, "max": 10, "step": 1},
    "fraction-bar": {"total": 8, "filled": 3},
    "decimal-grid": {"columns": 10, "rows": 10, "filled": 25},
    "analog-clock": {"hour": 3, "minute": 30},
    "ruler": {"length": 180, "ticks": 9},
    "solid": {"solidType": "cube"},
    "net": {"solidType": "cube"},
    "transform-grid": {"grid": [5, 5], "shapePoints": [[0, 0]], "operation": "translation", "params": [1, 1], "showImage": False},
    "symmetry": {"axis": "vertical"},
    "perimeter-area": {"grid": [5, 5]},
    "volume": {"cubes": 8},
    "table": {"columns": 4, "rows": 4},
    "chart": {"values": [3, 5, 2]},
    "probability": {"sectors": 4},
}


def main() -> int:
    registry = load_registry()
    # Golden positives: fixed normalized params must produce identical SVG.
    for diagram_type, params in FIXTURES.items():
        first = render({"kind": diagram_type, "params": params}, 0, 0, THEME)
        second = render({"kind": diagram_type, "params": params}, 0, 0, THEME)
        assert first == second and first.startswith("<"), f"non-deterministic {diagram_type}"
    # Intentional failing fixture: undeclared parameters must be rejected before rendering.
    registry = {**registry, "workbooks": {"fixture": {"gradeBand": "3-4", "diagrams": {"q1": {"type": "number_line", "params": {"min": 0, "max": 1, "notAllowed": True}}}}}}
    try:
        diagram_spec(registry, "fixture", "q1")
    except ValueError as error:
        assert "undeclared params" in str(error)
    else:
        raise AssertionError("registry accepted an undeclared parameter")
    print(f"Diagram registry fixtures passed ({len(FIXTURES)} types + rejection fixture).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
