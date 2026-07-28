#!/usr/bin/env node
import path from "node:path";
import {
  assertString,
  fail,
  isPlainObject,
  loadCatalog,
  projectDir,
  readJson,
  workbookFiles,
} from "./lib/catalog-utils.mjs";

const ID = /^[a-z0-9][a-z0-9-]{2,63}$/;
const STANDARD_CODE = /^\[[0-9]+[가-힣][0-9]{2}-[0-9]{2}\]$/;
const SHA256 = /^[a-f0-9]{64}$/;
const PUBLIC_PATH = /^\/workbooks\/[a-z0-9][a-z0-9/_-]*\.(?:png|jpe?g|webp|pdf|html)$/;
const LEVELS = ["foundation", "standard", "challenge"];
const ROLES = new Set(["cover", "worksheet", "answer"]);
const GRADE_BANDS = new Set(["1-2", "3-4", "5-6"]);

function validatePage(page, workbook, index) {
  const label = `${workbook.id}.pages[${index}]`;
  if (!isPlainObject(page)) fail(`${label} must be an object`);
  assertString(page.id, `${label}.id`, { pattern: /^[a-z0-9-]+$/ });
  if (!Number.isInteger(page.order) || page.order < 1) fail(`${label}.order must be a positive integer`);
  if (!ROLES.has(page.role)) fail(`${label}.role must be cover, worksheet, or answer`);
  assertString(page.imagePath, `${label}.imagePath`, { pattern: PUBLIC_PATH });
  assertString(page.thumbnailPath, `${label}.thumbnailPath`, { pattern: PUBLIC_PATH });
  assertString(page.sha256, `${label}.sha256`, { pattern: SHA256 });
  assertString(page.alt, `${label}.alt`);
  if (typeof page.approved !== "boolean") fail(`${label}.approved must be boolean`);
}

export function validateWorkbook(workbook, source) {
  if (!isPlainObject(workbook)) fail(`${source} must contain an object`);
  const label = `Workbook ${source}`;
  for (const key of ["id", "slug", "title", "domain", "module", "author", "publishedAt", "transcriptPath"]) {
    assertString(workbook[key], `${label}.${key}`);
  }
  for (const key of ["id", "slug"]) assertString(workbook[key], `${label}.${key}`, { pattern: ID });
  if (!GRADE_BANDS.has(workbook.gradeBand)) fail(`${label}.gradeBand must be 1-2, 3-4, or 5-6`);
  if (workbook.grade !== undefined && ![1, 2, 3, 4, 5, 6].includes(workbook.grade)) fail(`${label}.grade must be 1–6 when supplied`);
  if (!Array.isArray(workbook.standardCodes) || workbook.standardCodes.length === 0) fail(`${label}.standardCodes must not be empty`);
  workbook.standardCodes.forEach((code, index) => assertString(code, `${label}.standardCodes[${index}]`, { pattern: STANDARD_CODE }));
  if (JSON.stringify(workbook.levels) !== JSON.stringify(LEVELS)) fail(`${label}.levels must exactly be foundation, standard, challenge`);
  if (!Array.isArray(workbook.pages) || workbook.pages.length === 0) fail(`${label}.pages must not be empty`);
  workbook.pages.forEach((page, index) => validatePage(page, workbook, index));
  const orders = workbook.pages.map((page) => page.order).sort((a, b) => a - b);
  if (orders.some((order, index) => order !== index + 1)) fail(`${label}.pages must have consecutive order values beginning at 1`);
  if (!isPlainObject(workbook.pdf)) fail(`${label}.pdf must be an object`);
  assertString(workbook.pdf.path, `${label}.pdf.path`, { pattern: PUBLIC_PATH });
  assertString(workbook.pdf.sha256, `${label}.pdf.sha256`, { pattern: SHA256 });
  if (!Number.isInteger(workbook.pdf.pageCount) || workbook.pdf.pageCount !== workbook.pages.length) fail(`${label}.pdf.pageCount must equal the number of pages`);
  assertString(workbook.transcriptPath, `${label}.transcriptPath`, { pattern: PUBLIC_PATH });
  if (workbook.license !== "CC-BY-NC-SA-4.0") fail(`${label}.license must be CC-BY-NC-SA-4.0`);
  if (workbook.author !== "Taehyeong Lim") fail(`${label}.author must be Taehyeong Lim`);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(workbook.publishedAt)) fail(`${label}.publishedAt must be YYYY-MM-DD`);
  if (typeof workbook.published !== "boolean") fail(`${label}.published must be boolean`);
  if (workbook.published && workbook.pages.some((page) => !page.approved)) fail(`${label} cannot be published before every page is approved`);
  return workbook;
}

export async function loadAndValidateContent() {
  const catalog = await loadCatalog();
  if (!isPlainObject(catalog) || catalog.version !== 1 || !Array.isArray(catalog.workbooks)) fail("content/catalog.json must be a version 1 catalog with a workbooks array");
  const files = await workbookFiles();
  const workbooks = await Promise.all(files.map(async (file) => validateWorkbook(await readJson(file), path.relative(projectDir, file))));
  const ids = new Set();
  const slugs = new Set();
  for (const workbook of workbooks) {
    if (ids.has(workbook.id)) fail(`Duplicate workbook id: ${workbook.id}`);
    if (slugs.has(workbook.slug)) fail(`Duplicate workbook slug: ${workbook.slug}`);
    ids.add(workbook.id); slugs.add(workbook.slug);
  }
  const catalogIds = catalog.workbooks.map((workbook) => workbook.id);
  if (new Set(catalogIds).size !== catalogIds.length) fail("content/catalog.json contains duplicate workbook IDs");
  if (catalogIds.length !== workbooks.length || catalogIds.some((id) => !ids.has(id))) {
    fail("content/catalog.json must list every and only workbook JSON file by its full object");
  }
  for (const catalogWorkbook of catalog.workbooks) {
    const sourceWorkbook = workbooks.find((workbook) => workbook.id === catalogWorkbook.id);
    if (JSON.stringify(catalogWorkbook) !== JSON.stringify(sourceWorkbook)) fail(`Catalog entry for ${catalogWorkbook.id} must exactly match its workbook JSON source`);
  }
  return { catalog, workbooks };
}

if (import.meta.main) {
  loadAndValidateContent()
    .then(({ workbooks }) => console.log(`Content validation passed (${workbooks.length} workbook${workbooks.length === 1 ? "" : "s"}).`))
    .catch((error) => { console.error(`Content validation failed: ${error.message}`); process.exitCode = 1; });
}
