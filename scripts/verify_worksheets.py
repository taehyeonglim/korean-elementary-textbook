#!/usr/bin/env python3
"""Mechanical production gate for deterministic worksheet assets.

Scores each workbook against pixel, correspondence, source text/calculation,
hash, PDF, and output-format checks. A workbook must score at least 95/100.
"""

from __future__ import annotations

import argparse
import html
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"
PUBLIC = ROOT / "public"
SVG_ROOT = ROOT / "artifacts" / "worksheet-svg"
REPORT_PATH = ROOT / "reports" / "worksheet-quality.json"
DIAGRAM_REGISTRY_PATH = ROOT / "config" / "diagram-registry.json"

GEOMETRY_MARKERS = {
    "two-digit-addition-subtraction": ["blank-place-value-grid"] * 6,
    "fractions": ["cells=8;filled=3", "cards=3;fractions=1/5,3/5,5/3", "bars=2;cells=4+4;filled=4+3", "bars=2;cells=7+7;filled=3+5", "equal-circles=2;sectors=3+5", "cards=4;empty-zones=1"],
    "angles": ["unit=degree", "rays=2;angle=60", "right-angle=90;bisector=45", "triangle-angles=50,60,70", "quadrilateral=generic;not-to-scale", "triples=40,65,75|40,65,80"],
    "plane-shapes": ["selectors=circle,triangle,rectangle", "selectors=circle,triangle,rectangle", "triangle;vertices=3", "quadrilateral;sides=4", "house=triangle1,rectangle1,circle1", "equilateral-triangles=2;shared-side=1;exterior=4"],
    "ratios-and-rates": ["red=6;yellow=4", "grid=20;filled=8", "conversion-boxes=3;empty=3", "conversion-boxes=3;empty=3", "grid=25;filled=0", "bars=18/24,21/30;fills=.75,.70;percent-labels=0"],
    "circle-pi-area": ["circle;diameter=10", "circle;radius=4", "circle;circumference=62.8;diameter=unknown", "circle;diameter=12", "circle;radius=5;loops=3", "square-side=14;inscribed-circle=1"],
}

PRIMITIVE_MINIMUMS = {
    "fractions": [{"rect": 8}, {"rect": 3}, {"rect": 8}, {"rect": 14}, {"path": 8}, {"rect": 4}],
    "angles": [{"text": 1}, {"path": 2}, {"path": 3}, {"polygon": 1}, {"polygon": 1}, {"text": 2}],
    "plane-shapes": [{"circle": 1, "polygon": 1, "rect": 1}, {"circle": 1, "polygon": 1, "rect": 1}, {"polygon": 1, "circle": 3}, {"rect": 1, "polygon": 1}, {"polygon": 1, "rect": 1, "circle": 1}, {"polygon": 2, "line": 1}],
    "ratios-and-rates": [{"circle": 10}, {"rect": 20}, {"rect": 3}, {"rect": 3}, {"rect": 25}, {"rect": 4}],
    "circle-pi-area": [{"circle": 1, "line": 1}, {"circle": 1, "line": 1}, {"circle": 1}, {"circle": 1, "line": 1}, {"circle": 2, "path": 1}, {"rect": 1, "circle": 1}],
    "two-digit-addition-subtraction": [{"rect": 9, "line": 2}] * 6,
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def svg_path(workbook: dict[str, Any], page: dict[str, Any]) -> Path:
    return SVG_ROOT / workbook["slug"] / Path(page["imagePath"]).with_suffix(".svg").name


def pdf_page_count(path: Path) -> int:
    result = subprocess.run(["pdfinfo", str(path)], text=True, capture_output=True, check=True)
    match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
    if not match:
        raise ValueError(f"Cannot read page count from {path}")
    return int(match.group(1))


def equation_values(text: str) -> list[str]:
    """Check only terminal, plain-number equations in explanatory prose.

    Chained derivations, fractions, units and parenthesised expressions are
    pedagogically valid but are not safely parseable with a small evaluator;
    treating their intermediate fragments as complete equations caused false
    production failures (for example ``7÷2=7/2`` and ``1,000``).
    """
    values: list[str] = []
    normalized_text = re.sub(r"(?<=\d),(?=\d)", "", text)
    pattern = r"(?<![0-9+×÷*/\-(])([0-9.]+(?:\s*[+×÷-]\s*[0-9.]+)+)\s*=\s*([0-9.]+)(?![0-9+×÷*/.-])"
    for expression, expected in re.findall(pattern, normalized_text):
        normalized = expression.replace("×", "*").replace("÷", "/").replace(" ", "")
        try:
            actual = eval(normalized, {"__builtins__": {}}, {})  # fixed numeric characters from JSON only
        except Exception:
            continue
        if abs(float(actual) - float(expected)) > 1e-8:
            values.append(f"incorrect equation {expression}={expected}")
    return values


def check_image(path: Path, required_format: str) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing {path.relative_to(ROOT)}"]
    with Image.open(path) as image:
        if image.size != (2480, 3508):
            errors.append(f"{path.name} dimensions {image.size}, expected A4 300dpi (2480x3508)")
        if image.format != required_format:
            errors.append(f"{path.name} format {image.format}, expected {required_format}")
    return errors


def source_contains(source: str, value: str) -> bool:
    """Compare SVG text regardless of tspan word wrapping."""
    source_text = html.unescape(re.sub(r"<[^>]+>", "", source))
    return re.sub(r"\s+", "", value) in re.sub(r"\s+", "", source_text)


def diagram_source(source: str, question_number: int) -> str:
    match = re.search(rf'<g id="diagram-q{question_number}"[^>]*>(.*?)</g>', source, re.DOTALL)
    return match.group(1) if match else ""


def angle_at(vertex: tuple[float, float], left: tuple[float, float], right: tuple[float, float]) -> float:
    left_vector = (left[0] - vertex[0], left[1] - vertex[1])
    right_vector = (right[0] - vertex[0], right[1] - vertex[1])
    dot = left_vector[0] * right_vector[0] + left_vector[1] * right_vector[1]
    left_length = (left_vector[0] ** 2 + left_vector[1] ** 2) ** .5
    right_length = (right_vector[0] ** 2 + right_vector[1] ** 2) ** .5
    from math import acos, degrees
    return degrees(acos(max(-1.0, min(1.0, dot / (left_length * right_length)))))


def assert_angles_triangle(diagram: str) -> str | None:
    match = re.search(r'<polygon points="([^"]+)"', diagram)
    if not match:
        return "angle q4 lacks a triangle polygon"
    points = []
    for pair in match.group(1).split():
        x, y = pair.split(",")
        points.append((float(x), float(y)))
    if len(points) != 3:
        return "angle q4 triangle must have exactly three vertices"
    left_angle = angle_at(points[0], points[1], points[2])
    right_angle = angle_at(points[1], points[0], points[2])
    if abs(left_angle - 50) > .5 or abs(right_angle - 60) > .5:
        return f"angle q4 polygon geometry is {left_angle:.1f}°/{right_angle:.1f}°, expected 50°/60°"
    return None


def verify_workbook(workbook: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    checks = {"pixels": 20, "formats": 10, "question_answer_correspondence": 20, "geometry": 10, "source_text_and_calculation": 5, "answer_level_color": 5, "hashes": 15, "pdf": 15}
    deductions = {key: 0 for key in checks}
    page_by_id = {page["id"]: page for page in workbook["pages"]}
    generated_ids = ["worksheet-1", "worksheet-2", "answers"]
    svg_texts: dict[str, str] = {}

    for page_id in generated_ids:
        page = page_by_id.get(page_id)
        if not page:
            errors.append(f"missing expected page record {page_id}")
            deductions["question_answer_correspondence"] += 8
            continue
        png = PUBLIC / page["imagePath"].lstrip("/")
        webp = PUBLIC / page["thumbnailPath"].lstrip("/")
        image_errors = check_image(png, "WEBP" if page["imagePath"].endswith(".webp") else "PNG")
        webp_errors = [] if png == webp else check_image(webp, "WEBP")
        if image_errors:
            errors.extend(image_errors); deductions["pixels"] += 7
        if webp_errors:
            errors.extend(webp_errors); deductions["formats"] += 4
        source = svg_path(workbook, page)
        if not source.exists():
            errors.append(f"missing SVG source {source.relative_to(ROOT)}")
            deductions["source_text_and_calculation"] += 5
            continue
        svg_texts[page_id] = source.read_text(encoding="utf-8")
        for required_credit in ("Taehyeong Lim", "CC BY-NC-SA 4.0", "Gongnyang Prompt Kit"):
            if required_credit not in svg_texts[page_id]:
                errors.append(f"{page_id} lacks required credit: {required_credit}")
                deductions["source_text_and_calculation"] += 5
        if png.exists() and sha256(png) != page["sha256"]:
            errors.append(f"PNG hash mismatch {page['imagePath']}")
            deductions["hashes"] += 5

    questions = workbook.get("questions", [])
    if len(questions) != 6:
        errors.append(f'expected 6 questions, found {len(questions)}')
        deductions["question_answer_correspondence"] += 25
    else:
        for page_id, page_questions in (("worksheet-1", questions[:3]), ("worksheet-2", questions[3:])):
            text = svg_texts.get(page_id, "")
            for local_index, question in enumerate(page_questions):
                question_index = (0 if page_id == "worksheet-1" else 3) + local_index
                if not source_contains(text, question["prompt"]) or not source_contains(text, question["standardCode"]):
                    errors.append(f'{page_id} does not include {question["id"]} prompt/standard')
                    deductions["question_answer_correspondence"] += 3
                marker = GEOMETRY_MARKERS.get(workbook["id"], ["student-workspace"] * 6)[question_index]
                diagram = diagram_source(text, question_index + 1)
                if (workbook["id"] in GEOMETRY_MARKERS and marker not in text) or not diagram:
                    errors.append(f'{page_id} diagram q{question_index + 1} lacks geometry marker')
                    deductions["geometry"] += 2
                # Legacy diagrams have content-specific primitive contracts.
                # Registry diagrams are validated by their nonempty q-level
                # group and geometry metadata above; a clock or solid need not
                # contain a rectangle.
                minimums = PRIMITIVE_MINIMUMS.get(workbook["id"], [{}] * 6)[question_index]
                for tag, minimum in minimums.items():
                    if len(re.findall(rf'<{tag}(?:\s|/|>)', diagram)) < minimum:
                        errors.append(f'{page_id} diagram q{question_index + 1} has insufficient {tag} primitives')
                        deductions["geometry"] += 2
                if workbook["id"] == "angles" and question_index == 3:
                    geometry_error = assert_angles_triangle(diagram)
                    if geometry_error:
                        errors.append(geometry_error)
                        deductions["geometry"] += 5
                # Only question-given information may appear in a problem diagram.
                # Answers already present in the prompt are allowed; derived answers are not.
                if question["answer"] not in question["prompt"] and source_contains(diagram, question["answer"]):
                    errors.append(f'{page_id} diagram q{question_index + 1} leaks its derived answer')
                    deductions["question_answer_correspondence"] += 3
        answer_svg = svg_texts.get("answers", "")
        for question in questions:
            if not source_contains(answer_svg, question["answer"]) or not source_contains(answer_svg, question["explanation"]):
                errors.append(f'answer page does not include {question["id"]} answer/explanation')
                deductions["question_answer_correspondence"] += 3
            for calculation_error in equation_values(question["explanation"]):
                errors.append(f'{question["id"]}: {calculation_error}')
                deductions["source_text_and_calculation"] += 4
        expected_levels = [question["level"] for question in questions]
        for index, level in enumerate(expected_levels, start=1):
            expected_fill = {"foundation": "#DDF3E4", "standard": "#DDEBFA", "challenge": "#FDE6D7"}[level]
            pattern = rf'data-answer-level="{level}" fill="{re.escape(expected_fill)}"'
            if not re.search(pattern, answer_svg):
                errors.append(f'answer card {index} lacks {level} level color mapping')
                deductions["answer_level_color"] += 1

    pdf = PUBLIC / workbook["pdf"]["path"].lstrip("/")
    if not pdf.exists():
        errors.append(f"missing PDF {pdf.relative_to(ROOT)}")
        deductions["pdf"] += 15
    else:
        try:
            if pdf_page_count(pdf) != 4:
                errors.append(f"PDF is not 4 pages: {pdf.relative_to(ROOT)}")
                deductions["pdf"] += 10
        except Exception as error:
            errors.append(str(error)); deductions["pdf"] += 10
        if sha256(pdf) != workbook["pdf"]["sha256"]:
            errors.append(f"PDF hash mismatch {workbook['pdf']['path']}")
            deductions["hashes"] += 8

    deductions = {key: min(value, points) for key, (value, points) in ((key, (deductions[key], checks[key])) for key in checks)}
    score = max(0, 100 - sum(deductions.values()))
    return {"id": workbook["id"], "score": score, "passed": score >= 95 and not errors, "checks": checks, "deductions": deductions, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    catalog = read_json(CONTENT / "catalog.json")
    results = [verify_workbook(workbook) for workbook in catalog["workbooks"]]
    registry = read_json(DIAGRAM_REGISTRY_PATH)
    fallback_reasons: dict[str, int] = {}
    assigned = 0
    for assignment in registry.get("workbooks", {}).values():
        for spec in assignment.get("diagrams", {}).values():
            assigned += 1
            reason = spec.get("fallbackReason")
            if reason:
                fallback_reasons[reason] = fallback_reasons.get(reason, 0) + 1
    report = {
        "schemaVersion": 2,
        "minimumScore": 95,
        "diagramAssignments": {
            "reviewedWorkbookCount": len(registry.get("workbooks", {})),
            "assignedQuestionCount": assigned,
            "fallbackQuestionCount": sum(fallback_reasons.values()),
            "fallbackReasons": fallback_reasons,
            "note": "Fallback means an intentionally blank student workspace for a text-only calculation; it is never an unassigned visual prompt.",
        },
        "workbooks": results,
        "overallPassed": all(result["passed"] for result in results),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for result in results:
        print(f'{result["id"]}: {result["score"]}/100 {"PASS" if result["passed"] else "FAIL"}')
        for error in result["errors"]:
            print(f"  - {error}")
    print(f"Quality report: {args.report.relative_to(ROOT)}")
    return 0 if report["overallPassed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
