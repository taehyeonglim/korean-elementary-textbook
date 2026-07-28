#!/usr/bin/env node
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { PDFDocument } from "pdf-lib";
import { fail, sha256, toPublicFile } from "./lib/catalog-utils.mjs";
import { loadAndValidateContent } from "./validate-content.mjs";

const A4 = [595.28, 841.89];

function argument(name) {
  const index = process.argv.indexOf(name);
  return index === -1 ? undefined : process.argv[index + 1];
}

async function embedImage(pdf, source) {
  const bytes = await readFile(source);
  const extension = path.extname(source).toLowerCase();
  if (extension === ".png") return pdf.embedPng(bytes);
  if (extension === ".jpg" || extension === ".jpeg") return pdf.embedJpg(bytes);
  fail(`PDF assembly accepts approved PNG/JPEG originals only, not ${extension}: ${source}`);
}

export async function buildPdf(workbookId) {
  if (!workbookId) fail("Usage: npm run build:pdf -- --workbook <id>");
  const { workbooks } = await loadAndValidateContent();
  const workbook = workbooks.find((item) => item.id === workbookId);
  if (!workbook) fail(`Unknown workbook: ${workbookId}`);
  if (workbook.pages.some((page) => !page.approved)) fail(`${workbook.id} has unapproved pages; PDF assembly is blocked`);
  const pdf = await PDFDocument.create();
  pdf.setTitle(workbook.title);
  pdf.setAuthor(workbook.author);
  pdf.setSubject(`${workbook.standardCodes.join(", ")} · ${workbook.license}`);
  pdf.setKeywords(["초등 수학", "학습지", ...workbook.standardCodes, workbook.license]);
  pdf.setCreator("초등 수학 한 장 static asset pipeline");

  for (const pageInfo of [...workbook.pages].sort((a, b) => a.order - b.order)) {
    const image = await embedImage(pdf, toPublicFile(pageInfo.imagePath));
    const page = pdf.addPage(A4);
    const scale = Math.min(A4[0] / image.width, A4[1] / image.height);
    const width = image.width * scale;
    const height = image.height * scale;
    page.drawImage(image, { x: (A4[0] - width) / 2, y: (A4[1] - height) / 2, width, height });
  }
  const target = toPublicFile(workbook.pdf.path);
  await writeFile(target, await pdf.save());
  console.log(`${workbook.pdf.path} written; update its sha256 in the workbook source to ${await sha256(target)}.`);
}

if (import.meta.main) {
  buildPdf(argument("--workbook")).catch((error) => { console.error(`PDF assembly failed: ${error.message}`); process.exitCode = 1; });
}
