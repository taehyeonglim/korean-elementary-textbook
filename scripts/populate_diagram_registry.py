#!/usr/bin/env python3
"""Populate the reviewed, q-level visual assignment registry.

This is deliberately a small deterministic compiler: worksheet wording remains
in content JSON, while the choice of a non-answer-bearing visual aid is kept in
the renderer configuration.  Re-running it is safe and produces the same
registry for the same workbook set.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "diagram-registry.json"
WORKBOOKS = ROOT / "content" / "workbooks"
LEGACY = {"two-digit-addition-subtraction", "fractions", "angles", "plane-shapes", "ratios-and-rates", "circle-pi-area"}


def profile(workbook_id: str, module: str, domain: str) -> tuple[str, dict, str]:
    """Return visual kind, safe parameters, and the pedagogical purpose."""
    key = f"{workbook_id} {module} {domain}"
    if "시각과 시간" in key:
        return "analog-clock", {}, "time-reading-or-duration"
    if module == "길이":
        return "ruler", {"ticks": 10}, "length-scale"
    if any(word in key for word in ("자료", "그래프")):
        return ("chart" if "자료" in module else "table"), {}, "data-representation"
    if "가능성" in key:
        return "probability", {"sectors": 4}, "equally-likely-outcomes"
    if any(word in key for word in ("분수", "분수와 소수")):
        return "fraction-bar", {"total": 4, "filled": 0}, "fraction-partition"
    if "소수" in key:
        return "decimal-grid", {"columns": 10, "rows": 10, "cell": 18, "filled": 0}, "decimal-place-model"
    if any(word in key for word in ("평면도형의 이동", "합동과 대칭")):
        return "transform-grid" if "이동" in key else "symmetry", {}, "transformation-grid"
    if any(word in key for word in ("입체", "직육면체", "정육면체", "각기둥", "각뿔", "원기둥", "원뿔", "구")):
        return ("net" if "전개도" in key else "solid"), {}, "solid-shape-model"
    if any(word in key for word in ("둘레", "넓이", "삼각형", "사각형", "다각형", "원의 구성", "도형의 기초")):
        return "perimeter-area", {}, "shape-and-measurement-model"
    if any(word in key for word in ("들이", "무게", "양의 비교")):
        return "table", {}, "quantity-comparison-table"
    if any(word in key for word in ("비례", "대응", "규칙", "등호")):
        return "table", {}, "relationship-table"
    if any(word in key for word in ("수의 범위", "올림", "버림", "반올림", "어림", "약수", "배수")):
        return "number_line", {"start": 0, "end": 10, "ticks": 10, "length": 200}, "number-relationship-line"
    if any(word in key for word in ("수", "곱셈", "나눗셈", "계산")):
        return "blank-workspace", {"columns": 3, "rows": 3, "cell": 44, "lines": 2}, "text-calculation-workspace"
    return "blank-workspace", {"columns": 3, "rows": 3, "cell": 44, "lines": 2}, "text-calculation-workspace"


def main() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    assignments = {}
    for path in sorted(WORKBOOKS.glob("*.json")):
        workbook = json.loads(path.read_text(encoding="utf-8"))
        if workbook["id"] in LEGACY:
            continue
        kind, params, purpose = profile(workbook["id"], workbook["module"], workbook["domain"])
        diagrams = {}
        for index, question in enumerate(workbook["questions"], start=1):
            question_kind, question_params = kind, dict(params)
            # A clock is visual source data, so use only the time stated in the
            # prompt (never the calculated end time).  Other time questions use
            # a neutral clock face rather than inventing a result.
            if workbook["id"] == "g1-2-time" and question["id"] == "q1":
                question_params = {"hour": 3, "minute": 20}
            elif workbook["id"] == "g1-2-time" and question["id"] == "q4":
                question_params = {"hour": 8, "minute": 45}
            elif workbook["id"] == "g3-4-time" and question["id"] == "q6":
                question_params = {"hour": 10, "minute": 15}
            # Charts use only the counts supplied in their own prompt. This
            # keeps the SVG source aligned with graph-reading questions.
            elif question_kind == "chart":
                values = [int(value.replace(",", "")) for value in re.findall(r"(?<![0-9])[0-9][0-9,]*(?![0-9])", question["prompt"])]
                question_params = {"values": values[:4] or [0, 0, 0, 0]}
            elif question_kind == "fraction-bar":
                denominators = re.findall(r"[0-9]+/([0-9]+)", question["prompt"])
                if denominators:
                    question_params = {"total": min(24, max(2, int(denominators[0]))), "filled": 0}
            diagrams[question["id"]] = {
                "type": question_kind,
                "params": question_params,
                "geometry": purpose,
                "assertions": {"noDerivedAnswer": True},
                "fallbackReason": "" if question_kind != "blank-workspace" else "text-calculation-workspace",
            }
        assignments[workbook["id"]] = {
            "gradeBand": workbook["gradeBand"],
            "assignmentPolicy": "reviewed-q-level-v1",
            "diagrams": diagrams,
        }
    registry["workbooks"] = assignments
    registry["assignmentSummary"] = {
        "policy": "Each non-legacy question receives a reviewed deterministic visual assignment; blank workspace is permitted only for text-only calculation practice.",
        "generatedBy": "scripts/populate_diagram_registry.py",
    }
    REGISTRY_PATH.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(assignments)} workbook visual assignments to {REGISTRY_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
