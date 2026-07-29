#!/usr/bin/env node
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { projectDir, fail, loadCatalog, readJson } from "./lib/catalog-utils.mjs";

const distDir = path.join(projectDir, "dist");
const ALLOWED_EXTENSIONS = new Set([".html", ".css", ".js", ".json", ".map", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".ico", ".pdf", ".txt", ".xml", ".woff", ".woff2"]);
const FORBIDDEN_PATH_PARTS = ["prompt", "snapshot", "private", ".env", "credential", "secret"];
const FORBIDDEN_CONTENT = [/api[_-]?key/i, /BEGIN (?:RSA |OPENSSH )?PRIVATE KEY/, /curriculum.*mcp.*raw/i];

async function filesIn(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map(async (entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? filesIn(target) : [target];
  }));
  return nested.flat();
}

async function assertPage(relative, snippets = []) {
  const target = path.join(distDir, relative, "index.html");
  let body;
  try {
    body = await readFile(target, "utf8");
  } catch {
    fail(`Missing required page: ${relative || "/"}`);
  }
  for (const snippet of snippets) {
    if (!body.includes(snippet)) fail(`Required page ${relative || "/"} is missing: ${snippet}`);
  }
  return body;
}

export async function checkPublicOutput() {
  const files = await filesIn(distDir);
  for (const file of files) {
    const relative = path.relative(distDir, file).replaceAll(path.sep, "/");
    if (path.basename(file) === ".gitkeep") continue;
    const extension = path.extname(file).toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(extension)) fail(`Disallowed public artifact extension: ${relative}`);
    if (FORBIDDEN_PATH_PARTS.some((part) => relative.toLowerCase().includes(part))) fail(`Potentially private artifact in Pages output: ${relative}`);
    if ([".html", ".json", ".js", ".txt", ".xml"].includes(extension)) {
      const body = await readFile(file, "utf8");
      if (FORBIDDEN_CONTENT.some((pattern) => pattern.test(body))) fail(`Potentially private data in Pages output: ${relative}`);
    }
  }

  const catalog = await loadCatalog();
  const publishedMath = catalog.workbooks.filter((workbook) => workbook.published === true && workbook.subject === "math");
  const publishedEnglish = catalog.workbooks.filter((workbook) => workbook.published === true && workbook.subject === "english");
  const englishSummary = await readJson(path.join(projectDir, "content", "curriculum", "english-summary-2026-07-29.json"));

  await assertPage("", ["초등 학습지 한 장", "초등 수학 한 장", "초등 영어 한 장"]);
  const mathArchive = await assertPage("math", ["초등 수학 한 장", `${publishedMath.length}권`]);
  const englishArchive = await assertPage("english", [
    "초등 영어 한 장",
    `${englishSummary.standardCount}`,
    "이해",
    "표현",
    `${publishedEnglish.length}권 무료 배포 중`
  ]);
  await assertPage("license", ["이용 안내"]);

  for (const workbook of publishedMath) {
    const newRoute = `math/workbooks/${workbook.slug}`;
    const legacyRoute = `workbooks/${workbook.slug}`;
    await assertPage(newRoute, [workbook.title]);
    const legacy = await assertPage(legacyRoute, [newRoute, "새 주소로 이동"]);
    if (!legacy.includes('http-equiv="refresh"')) fail(`Legacy route does not redirect: ${legacyRoute}`);
    if (!mathArchive.includes(`${newRoute}/`)) fail(`Math archive does not link to: ${newRoute}`);
  }
  for (const workbook of publishedEnglish) {
    const route = `english/workbooks/${workbook.slug}`;
    await assertPage(route, [workbook.title.split("&")[0].trim(), `${workbook.pdf.pageCount}쪽`]);
    if (!englishArchive.includes(`${route}/`)) fail(`English archive does not link to: ${route}`);
  }

  if (englishSummary.gradeBands["3-4"].standardCount !== 20 || englishSummary.gradeBands["5-6"].standardCount !== 20) {
    fail("English curriculum summary must contain 20 standards in each grade band.");
  }
  if (englishSummary.officialAreas.map((area) => area.labelKorean).join(",") !== "이해,표현") {
    fail("English curriculum summary must preserve the official understanding/expression areas.");
  }

  console.log(`Public output validation passed (${files.length} files, ${publishedMath.length} math and ${publishedEnglish.length} English workbooks).`);
}

if (import.meta.main) {
  checkPublicOutput().catch((error) => { console.error(`Public output validation failed: ${error.message}`); process.exitCode = 1; });
}
