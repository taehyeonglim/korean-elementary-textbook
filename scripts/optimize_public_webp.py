#!/usr/bin/env python3
"""Publish WebP pages only; PNGs remain renderer intermediates, never assets."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC, CONTENT = ROOT / "public", ROOT / "content"

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    records = []
    for path in sorted((CONTENT / "workbooks").glob("*.json")):
        workbook = json.loads(path.read_text())
        for page in workbook["pages"]:
            webp = PUBLIC / page["thumbnailPath"].lstrip("/")
            if not webp.exists(): raise FileNotFoundError(webp)
            page["imagePath"] = page["thumbnailPath"]
            page["sha256"] = digest(webp)
        pdf = PUBLIC / workbook["pdf"]["path"].lstrip("/")
        if not pdf.exists(): raise FileNotFoundError(pdf)
        workbook["pdf"]["sha256"] = digest(pdf)
        path.write_text(json.dumps(workbook, ensure_ascii=False, indent=2) + "\n")
        records.append(workbook)
    catalog_path = CONTENT / "catalog.json"
    catalog = json.loads(catalog_path.read_text())
    catalog["workbooks"] = records
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n")
    for png in (PUBLIC / "workbooks").rglob("*.png"):
        png.unlink()
    print(f"Published {len(records)} WebP-only workbooks; removed PNG intermediates.")

if __name__ == "__main__": main()
