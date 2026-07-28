import { createHash } from "node:crypto";
import { access, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const projectDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
export const contentDir = path.join(projectDir, "content");
export const workbookDir = path.join(contentDir, "workbooks");
export const publicDir = path.join(projectDir, "public");

export function fail(message) {
  throw new Error(message);
}

export async function fileExists(target) {
  try {
    await access(target);
    return true;
  } catch {
    return false;
  }
}

export async function readJson(target) {
  try {
    return JSON.parse(await readFile(target, "utf8"));
  } catch (error) {
    fail(`Cannot parse JSON at ${path.relative(projectDir, target)}: ${error.message}`);
  }
}

export async function loadCatalog() {
  return readJson(path.join(contentDir, "catalog.json"));
}

export async function workbookFiles() {
  const entries = await readdir(workbookDir, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => path.join(workbookDir, entry.name))
    .sort();
}

export function toPublicFile(publicPath) {
  if (typeof publicPath !== "string" || !publicPath.startsWith("/workbooks/")) {
    fail(`Expected an asset path under /workbooks/, got ${String(publicPath)}`);
  }
  const target = path.resolve(publicDir, `.${publicPath}`);
  if (!target.startsWith(`${publicDir}${path.sep}`)) fail(`Unsafe public path: ${publicPath}`);
  return target;
}

export async function sha256(target) {
  return createHash("sha256").update(await readFile(target)).digest("hex");
}

export function isPlainObject(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

export function assertString(value, label, { pattern, nonEmpty = true } = {}) {
  if (typeof value !== "string" || (nonEmpty && value.trim() === "")) fail(`${label} must be a non-empty string`);
  if (pattern && !pattern.test(value)) fail(`${label} has an invalid format: ${value}`);
}
