#!/usr/bin/env node
import { readdir, readFile } from "node:fs/promises";
import path from "node:path";
import { projectDir, fail } from "./lib/catalog-utils.mjs";

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
  console.log(`Public output allowlist passed (${files.length} files).`);
}

if (import.meta.main) {
  checkPublicOutput().catch((error) => { console.error(`Public output validation failed: ${error.message}`); process.exitCode = 1; });
}
