#!/usr/bin/env node
import { mkdir } from "node:fs/promises";
import path from "node:path";
import sharp from "sharp";
import { fail, toPublicFile } from "./lib/catalog-utils.mjs";
import { loadAndValidateContent } from "./validate-content.mjs";

function argument(name) {
  const index = process.argv.indexOf(name);
  return index === -1 ? undefined : process.argv[index + 1];
}

export async function buildThumbnails(workbookId) {
  if (!workbookId) fail("Usage: npm run build:thumbnails -- --workbook <id>");
  const { workbooks } = await loadAndValidateContent();
  const workbook = workbooks.find((item) => item.id === workbookId);
  if (!workbook) fail(`Unknown workbook: ${workbookId}`);
  for (const page of workbook.pages) {
    const source = toPublicFile(page.imagePath);
    const target = toPublicFile(page.thumbnailPath);
    if (path.extname(target).toLowerCase() !== ".webp") fail(`${page.thumbnailPath} must use the .webp extension`);
    await mkdir(path.dirname(target), { recursive: true });
    await sharp(source).resize({ width: 720, withoutEnlargement: true }).webp({ quality: 82 }).toFile(target);
    console.log(`Created ${page.thumbnailPath}`);
  }
}

if (import.meta.main) {
  buildThumbnails(argument("--workbook")).catch((error) => { console.error(`Thumbnail build failed: ${error.message}`); process.exitCode = 1; });
}
