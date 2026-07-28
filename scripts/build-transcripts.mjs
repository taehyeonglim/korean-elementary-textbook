#!/usr/bin/env node
import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { projectDir, toPublicFile, fail } from "./lib/catalog-utils.mjs";
import { loadAndValidateContent } from "./validate-content.mjs";

const manifestPath = path.join(projectDir, "prompts", "generation-manifest.json");

export async function buildTranscripts() {
  const [{ workbooks }, manifest] = await Promise.all([
    loadAndValidateContent(),
    readFile(manifestPath, "utf8").then(JSON.parse),
  ]);
  if (!Array.isArray(manifest.workbooks)) fail("generation manifest must contain a workbooks array");
  const manifests = new Map(manifest.workbooks.map((item) => [item.id, item]));

  for (const workbook of workbooks) {
    const source = manifests.get(workbook.id);
    if (!source || typeof source.transcriptHtml !== "string" || source.transcriptHtml.trim() === "") {
      fail(`${workbook.id}: generation manifest has no transcriptHtml`);
    }
    if (source.transcriptPath !== workbook.transcriptPath) {
      fail(`${workbook.id}: transcript path differs between workbook and generation manifest`);
    }
    const target = toPublicFile(workbook.transcriptPath);
    await mkdir(path.dirname(target), { recursive: true });
    await writeFile(target, `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${workbook.title} 문항·정답 전문</title></head><body>${source.transcriptHtml}</body></html>\n`);
    console.log(`Created ${workbook.transcriptPath}`);
  }
}

if (import.meta.main) {
  buildTranscripts().catch((error) => { console.error(`Transcript build failed: ${error.message}`); process.exitCode = 1; });
}
