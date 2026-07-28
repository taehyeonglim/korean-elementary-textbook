#!/usr/bin/env node
import { PDFDocument } from "pdf-lib";
import sharp from "sharp";
import {
  fail,
  fileExists,
  sha256,
  toPublicFile,
} from "./lib/catalog-utils.mjs";
import { loadAndValidateContent } from "./validate-content.mjs";

async function validateImage(workbook, page) {
  const source = toPublicFile(page.imagePath);
  const thumbnail = toPublicFile(page.thumbnailPath);
  if (!(await fileExists(source))) fail(`${workbook.id}: missing approved image ${page.imagePath}`);
  if (!(await fileExists(thumbnail))) fail(`${workbook.id}: missing thumbnail ${page.thumbnailPath}`);
  if (await sha256(source) !== page.sha256) fail(`${workbook.id}: image hash does not match ${page.imagePath}`);
  const metadata = await sharp(source).metadata();
  if (!metadata.width || !metadata.height || metadata.width < 1000 || metadata.height < 1400) fail(`${workbook.id}: ${page.imagePath} must be a high-resolution portrait page`);
  if (metadata.width / metadata.height > 0.8) fail(`${workbook.id}: ${page.imagePath} must be portrait oriented`);
  const thumbMetadata = await sharp(thumbnail).metadata();
  if (thumbMetadata.format !== "webp") fail(`${workbook.id}: ${page.thumbnailPath} must be WebP`);
}

async function validatePdf(workbook) {
  const source = toPublicFile(workbook.pdf.path);
  if (!(await fileExists(source))) fail(`${workbook.id}: missing PDF ${workbook.pdf.path}`);
  if (await sha256(source) !== workbook.pdf.sha256) fail(`${workbook.id}: PDF hash does not match ${workbook.pdf.path}`);
  const document = await PDFDocument.load(await (await import("node:fs/promises")).readFile(source));
  if (document.getPageCount() !== workbook.pdf.pageCount) fail(`${workbook.id}: PDF page count does not match catalog`);
  const title = document.getTitle();
  const author = document.getAuthor();
  if (title !== workbook.title || author !== workbook.author) fail(`${workbook.id}: PDF metadata must carry workbook title and author`);
}

export async function validateAssets() {
  const { workbooks } = await loadAndValidateContent();
  for (const workbook of workbooks) {
    if (!workbook.published) continue;
    for (const page of workbook.pages) await validateImage(workbook, page);
    await validatePdf(workbook);
    const transcript = toPublicFile(workbook.transcriptPath);
    if (!(await fileExists(transcript))) fail(`${workbook.id}: missing accessible transcript ${workbook.transcriptPath}`);
  }
  return workbooks.filter((workbook) => workbook.published).length;
}

if (import.meta.main) {
  validateAssets()
    .then((count) => console.log(`Asset validation passed (${count} published workbook${count === 1 ? "" : "s"}).`))
    .catch((error) => { console.error(`Asset validation failed: ${error.message}`); process.exitCode = 1; });
}
