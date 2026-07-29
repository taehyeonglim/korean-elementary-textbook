#!/usr/bin/env python3
"""Rebuild printable PDFs from WebP pages at A4 200dpi JPEG quality 88."""
from __future__ import annotations
import hashlib, io, json
from pathlib import Path
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
PUBLIC, CONTENT = ROOT / "public", ROOT / "content"
TARGET = (1654, 2339)  # A4 at 200dpi

def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> None:
    entries=[]
    for record in sorted((CONTENT / "workbooks").glob("*.json")):
        workbook=json.loads(record.read_text())
        destination=PUBLIC / workbook["pdf"]["path"].lstrip("/")
        document=canvas.Canvas(str(destination), pagesize=A4, pageCompression=1)
        document.setTitle(workbook["title"]); document.setAuthor(workbook["author"])
        document.setSubject(f'{", ".join(workbook["standardCodes"])} · {workbook["license"]}')
        document.setCreator("초등 수학 한 장 print-PDF optimizer")
        pw, ph=A4
        for page in sorted(workbook["pages"], key=lambda value: value["order"]):
            source=PUBLIC / page["imagePath"].lstrip("/")
            with Image.open(source) as raw:
                image=raw.convert("RGB").resize(TARGET, Image.Resampling.LANCZOS)
                encoded=io.BytesIO(); image.save(encoded, "JPEG", quality=88, optimize=True, progressive=True)
            encoded.seek(0); document.drawImage(ImageReader(encoded), 0, 0, pw, ph, mask="auto"); document.showPage()
        document.save(); workbook["pdf"]["sha256"]=sha(destination)
        record.write_text(json.dumps(workbook, ensure_ascii=False, indent=2)+"\n"); entries.append(workbook)
    catalog_path=CONTENT / "catalog.json"; catalog=json.loads(catalog_path.read_text()); catalog["workbooks"]=entries
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+"\n")
    print(f"Optimized {len(entries)} PDFs at 200dpi JPEG quality 88.")

if __name__ == "__main__": main()
