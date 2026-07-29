#!/usr/bin/env node
import { execFile } from "node:child_process";
import { readFile } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { PDFDocument } from "pdf-lib";
import sharp from "sharp";
import {
  fail,
  fileExists,
  sha256,
  toPublicFile,
} from "./lib/catalog-utils.mjs";
import { loadAndValidateContent } from "./validate-content.mjs";

const execFileAsync = promisify(execFile);
const MP3_DURATION_TOLERANCE_SECONDS = 0.05;

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

async function validateAudio(workbook) {
  if (!workbook.audio) return;
  const { audio } = workbook;
  const source = toPublicFile(audio.path);
  const transcript = toPublicFile(audio.transcriptPath);
  const metadata = toPublicFile(audio.metadataPath);
  for (const [label, target] of [["MP3", source], ["listening transcript", transcript], ["audio metadata", metadata]]) {
    if (!(await fileExists(target))) fail(`${workbook.id}: missing ${label} ${path.basename(target)}`);
  }
  if (await sha256(source) !== audio.sha256) fail(`${workbook.id}: audio hash does not match ${audio.path}`);
  await execFileAsync("ffmpeg", ["-v", "error", "-i", source, "-f", "null", "-"], { windowsHide: true });
  const { stdout } = await execFileAsync("ffprobe", ["-v", "error", "-show_entries", "format=duration,format_name", "-of", "json", source], { windowsHide: true });
  const probe = JSON.parse(stdout);
  const duration = Number(probe?.format?.duration);
  // FFmpeg versions can include or exclude one MP3 frame of encoder padding.
  if (!String(probe?.format?.format_name || "").includes("mp3") || !Number.isFinite(duration) || Math.abs(duration - audio.durationSeconds) > MP3_DURATION_TOLERANCE_SECONDS) {
    fail(`${workbook.id}: audio decode metadata does not match catalog duration`);
  }
  const manifest = JSON.parse(await readFile(metadata, "utf8"));
  if (manifest.workbookId !== workbook.id || manifest.audio?.path !== audio.path || manifest.audio?.sha256 !== audio.sha256 || manifest.audio?.durationSeconds !== audio.durationSeconds) {
    fail(`${workbook.id}: audio metadata manifest is not synchronized with catalog`);
  }
  for (const field of ["backend", "model", "modelRevision", "modelSha256", "license", "disclosure", "transcriptPath"]) {
    if (manifest[field] !== audio[field]) fail(`${workbook.id}: audio metadata ${field} does not match catalog`);
  }
  if (JSON.stringify(manifest.voices) !== JSON.stringify(audio.voices)) fail(`${workbook.id}: audio metadata voices do not match catalog`);
  const transcriptText = await readFile(transcript, "utf8");
  if (!transcriptText.includes(audio.disclosure)) fail(`${workbook.id}: listening transcript omits AI disclosure`);
}

export async function validateAssets() {
  const { workbooks } = await loadAndValidateContent();
  for (const workbook of workbooks) {
    if (!workbook.published) continue;
    for (const page of workbook.pages) await validateImage(workbook, page);
    await validatePdf(workbook);
    const transcript = toPublicFile(workbook.transcriptPath);
    if (!(await fileExists(transcript))) fail(`${workbook.id}: missing accessible transcript ${workbook.transcriptPath}`);
    await validateAudio(workbook);
  }
  return workbooks.filter((workbook) => workbook.published).length;
}

if (import.meta.main) {
  validateAssets()
    .then((count) => console.log(`Asset validation passed (${count} published workbook${count === 1 ? "" : "s"}).`))
    .catch((error) => { console.error(`Asset validation failed: ${error.message}`); process.exitCode = 1; });
}
