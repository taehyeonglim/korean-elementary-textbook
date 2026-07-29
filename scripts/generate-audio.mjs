#!/usr/bin/env node
/**
 * Generate English listening assets from an approved, text-locked plan.
 *
 * Kokoro-82M is the default local backend. OpenAI remains available only when
 * a plan explicitly declares its OpenAI model and voices. Nothing in this
 * script touches public assets or content metadata until synthesis, MP3 decode,
 * transcript/manifest creation, and catalog synchronization have all passed.
 */
import { execFile } from "node:child_process";
import { copyFile, mkdtemp, mkdir, readFile, rename, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { promisify } from "node:util";
import { fileExists, projectDir, sha256, toPublicFile } from "./lib/catalog-utils.mjs";
import { loadAndValidateContent } from "./validate-content.mjs";

const execFileAsync = promisify(execFile);
const configPath = path.join(projectDir, "prompts", "audio-pilot.json");
const kokoroScript = path.join(projectDir, "scripts", "kokoro_tts.py");
const KOKORO_MODEL = "hexgrad/Kokoro-82M";
const KOKORO_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987";
const KOKORO_LICENSE = "Apache-2.0";

function fail(message) {
  throw new Error(message);
}

function parseArgs(argv) {
  const ids = new Set();
  let dryRun = false;
  let backend;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--workbook") {
      const id = argv[index + 1];
      if (!id || id.startsWith("--")) fail("--workbook requires a workbook ID");
      ids.add(id);
      index += 1;
    } else if (arg === "--backend") {
      backend = argv[index + 1];
      if (!backend || backend.startsWith("--")) fail("--backend requires kokoro or openai");
      if (!new Set(["kokoro", "openai"]).has(backend)) fail("--backend must be kokoro or openai");
      index += 1;
    } else if (arg === "--dry-run") dryRun = true;
    else if (arg === "--help") {
      console.log("Usage: node scripts/generate-audio.mjs [--workbook <id>] [--backend kokoro|openai] [--dry-run]");
      process.exit(0);
    } else fail(`Unknown option: ${arg}`);
  }
  return { ids, dryRun, backend };
}

function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function isSha256(value) {
  return typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
}

function audioIdentity(audio) {
  const { durationSeconds, sha256: outputSha256, ...identity } = audio;
  return identity;
}

function sameAudioIdentity(actual, expected) {
  return JSON.stringify(audioIdentity(actual)) === JSON.stringify(audioIdentity(expected));
}

function voiceMap(voices, label, requireHashes) {
  if (!Array.isArray(voices) || voices.length === 0) fail(`${label}.voices must be a non-empty array`);
  const result = new Map();
  for (const voice of voices) {
    if (!voice || typeof voice.role !== "string" || typeof voice.voice !== "string") fail(`${label}.voices entries require role and voice`);
    if (voice.locale !== "en-US") fail(`${label}.voices entries must declare locale en-US`);
    if ((requireHashes && !isSha256(voice.sha256)) || (!requireHashes && voice.sha256 !== null && !isSha256(voice.sha256))) {
      fail(`${label}.voices entries require ${requireHashes ? "a voice SHA-256" : "a SHA-256 or null"}`);
    }
    if (result.has(voice.role)) fail(`${label}.voices has a duplicate role: ${voice.role}`);
    result.set(voice.role, voice);
  }
  return result;
}

function validateAudioPlan(audio, label) {
  if (!audio || typeof audio !== "object") fail(`${label}.audio must be an object`);
  for (const field of ["path", "transcriptPath", "metadataPath", "backend", "model", "modelRevision", "license", "disclosure"]) {
    if (typeof audio[field] !== "string" || audio[field].trim() === "") fail(`${label}.audio.${field} must be a non-empty string`);
  }
  toPublicFile(audio.path);
  toPublicFile(audio.transcriptPath);
  toPublicFile(audio.metadataPath);
  if (audio.aiGenerated !== true) fail(`${label}.audio must declare aiGenerated:true`);
  if (audio.modelSha256 !== null && !isSha256(audio.modelSha256)) fail(`${label}.audio.modelSha256 must be a SHA-256 or null`);
  if (!Array.isArray(audio.playbackRates) || JSON.stringify(audio.playbackRates) !== JSON.stringify([0.75, 1])) {
    fail(`${label}.audio must use playbackRates [0.75,1]`);
  }
  if (!new Set(["kokoro", "openai"]).has(audio.backend)) fail(`${label}.audio.backend must be kokoro or openai`);
  if (audio.backend === "kokoro") {
    if (audio.model !== KOKORO_MODEL || audio.modelRevision !== KOKORO_REVISION || audio.license !== KOKORO_LICENSE) {
      fail(`${label}.audio Kokoro provenance must use the pinned official model revision and Apache-2.0 license`);
    }
  }
  return voiceMap(audio.voices, `${label}.audio`, audio.backend === "kokoro");
}

function assertPlanMatchesWorkbookText(workbook, plan, label) {
  if (!Array.isArray(workbook.activities?.text)) fail(`${label}: ${workbook.id} must have English activities.text`);
  const text = plan.segments.map((segment) => segment.text);
  if (JSON.stringify(text) !== JSON.stringify(workbook.activities.text)) {
    fail(`${label}: segments must exactly match the current workbook.activities.text`);
  }
}

function transcriptHtml(workbook, plan, audio) {
  const lines = plan.segments.map((segment) => `<li><strong>${escapeHtml(segment.role)}:</strong> <span lang="en">${escapeHtml(segment.text)}</span></li>`).join("\n");
  return `<!doctype html>
<html lang="ko">
  <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${escapeHtml(workbook.title)} 듣기 전문</title></head>
  <body><main><h1>${escapeHtml(workbook.title)} 듣기 전문</h1><p>${escapeHtml(audio.disclosure)}</p><p>이 전문은 ${escapeHtml(audio.model)} (${escapeHtml(audio.modelRevision)}) 음성과 같은 순서로 제공됩니다.</p><h2 lang="en">${escapeHtml(plan.title)}</h2><ol>${lines}</ol><p><a href="${escapeHtml(audio.metadataPath)}">음원 생성 정보(JSON)</a></p></main></body>
</html>
`;
}

async function requestOpenAiSpeech({ model, voice, input, role }) {
  if (!process.env.OPENAI_API_KEY) fail("OPENAI_API_KEY is required only for the explicitly selected openai backend");
  const response = await fetch("https://api.openai.com/v1/audio/speech", {
    method: "POST",
    headers: { Authorization: `Bearer ${process.env.OPENAI_API_KEY}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      model,
      voice,
      input,
      response_format: "mp3",
      instructions: `Speak as ${role} in clear, warm American English for elementary learners. Use a steady pace and natural short pauses.`,
    }),
  });
  if (!response.ok) fail(`OpenAI speech request failed (${response.status}): ${(await response.text()).slice(0, 600)}`);
  return Buffer.from(await response.arrayBuffer());
}

async function runKokoro(tempDir, plan, audio, voices) {
  const defaultPython = path.join(projectDir, ".generated", "kokoro-venv", "bin", "python");
  const python = process.env.KOKORO_PYTHON || defaultPython;
  if (!(await fileExists(python))) {
    fail(`Kokoro Python environment not found at ${path.relative(projectDir, python)}. Run npm run audio:setup-kokoro or set KOKORO_PYTHON.`);
  }
  const jobPath = path.join(tempDir, "kokoro-job.json");
  const wavPath = path.join(tempDir, "listening.wav");
  const provenancePath = path.join(tempDir, "kokoro-provenance.json");
  await writeFile(jobPath, `${JSON.stringify({
    backend: audio.backend,
    model: audio.model,
    modelRevision: audio.modelRevision,
    segments: plan.segments.map((segment) => ({ role: segment.role, text: segment.text, voice: voices.get(segment.role).voice })),
  }, null, 2)}\n`, "utf8");
  const venvBin = path.dirname(python);
  const venvRoot = path.dirname(venvBin);
  await execFileAsync(python, [kokoroScript, "--input", jobPath, "--output", wavPath, "--provenance", provenancePath], {
    windowsHide: true,
    env: { ...process.env, VIRTUAL_ENV: venvRoot, PATH: `${venvBin}${path.delimiter}${process.env.PATH || ""}`, HF_HUB_DISABLE_XET: "1" },
  });
  if (!(await fileExists(wavPath)) || !(await fileExists(provenancePath))) fail("Kokoro did not produce WAV and provenance outputs");
  const candidate = path.join(tempDir, "listening.mp3");
  await execFileAsync("ffmpeg", ["-y", "-v", "error", "-i", wavPath, "-ar", "24000", "-ac", "1", "-codec:a", "libmp3lame", "-b:a", "128k", candidate], { windowsHide: true });
  return { candidate, provenance: JSON.parse(await readFile(provenancePath, "utf8")) };
}

async function runOpenAi(tempDir, plan, audio, voices) {
  const segmentFiles = [];
  for (const [index, segment] of plan.segments.entries()) {
    const segmentPath = path.join(tempDir, `${String(index + 1).padStart(2, "0")}.mp3`);
    await writeFile(segmentPath, await requestOpenAiSpeech({ model: audio.model, voice: voices.get(segment.role).voice, input: segment.text, role: segment.role }));
    segmentFiles.push(segmentPath);
  }
  const listPath = path.join(tempDir, "concat.txt");
  await writeFile(listPath, segmentFiles.map((file) => `file '${file.replaceAll("'", "'\\''")}'`).join("\n"));
  const candidate = path.join(tempDir, "listening.mp3");
  await execFileAsync("ffmpeg", ["-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", listPath, "-codec:a", "libmp3lame", "-b:a", "128k", candidate], { windowsHide: true });
  return { candidate, provenance: { backend: "openai", model: audio.model, modelRevision: audio.modelRevision, sampleRate: 24000 } };
}

async function probeAudio(target) {
  await execFileAsync("ffmpeg", ["-v", "error", "-i", target, "-f", "null", "-"], { windowsHide: true });
  const { stdout } = await execFileAsync("ffprobe", ["-v", "error", "-show_entries", "format=duration,format_name", "-of", "json", target], { windowsHide: true });
  const info = JSON.parse(stdout);
  const durationSeconds = Number(info?.format?.duration);
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) fail(`Unable to determine a positive duration for ${target}`);
  if (!String(info?.format?.format_name || "").includes("mp3")) fail(`Expected MP3 output, received ${info?.format?.format_name || "unknown"}`);
  return { durationSeconds: Number(durationSeconds.toFixed(3)), sha256: await sha256(target) };
}

function finalAudioMetadata(audio, integrity) {
  return { ...audio, ...integrity };
}

async function stageContentMetadata(workbook, audio) {
  const sourcePath = path.join(projectDir, "content", "workbooks", `${workbook.id}.json`);
  const catalogPath = path.join(projectDir, "content", "catalog.json");
  const [source, catalog] = await Promise.all([readFile(sourcePath, "utf8").then(JSON.parse), readFile(catalogPath, "utf8").then(JSON.parse)]);
  if (source.id !== workbook.id) fail(`Source workbook mismatch at ${sourcePath}`);
  if (source.audio !== undefined && !sameAudioIdentity(source.audio, audio)) fail(`${workbook.id}: source audio provenance differs from the pending plan`);
  const entryIndex = catalog.workbooks?.findIndex((entry) => entry.id === workbook.id) ?? -1;
  if (entryIndex < 0) fail(`${workbook.id}: aggregate catalog has no matching entry`);
  if (catalog.workbooks[entryIndex].audio !== undefined && !sameAudioIdentity(catalog.workbooks[entryIndex].audio, audio)) fail(`${workbook.id}: catalog audio provenance differs from the pending plan`);
  source.audio = audio;
  catalog.workbooks[entryIndex] = source;
  const suffix = `.replacement-${process.pid}-${Date.now()}`;
  const sourceReplacement = `${sourcePath}${suffix}`;
  const catalogReplacement = `${catalogPath}${suffix}`;
  await Promise.all([
    writeFile(sourceReplacement, `${JSON.stringify(source, null, 2)}\n`, "utf8"),
    writeFile(catalogReplacement, `${JSON.stringify(catalog, null, 2)}\n`, "utf8"),
  ]);
  return [{ target: sourcePath, replacement: sourceReplacement }, { target: catalogPath, replacement: catalogReplacement }];
}

async function commitTransaction(replacements) {
  const backups = [];
  const committed = [];
  try {
    for (const replacement of replacements) {
      const exists = await fileExists(replacement.target);
      const backup = `${replacement.target}.backup-${process.pid}-${Date.now()}`;
      if (exists) await copyFile(replacement.target, backup);
      backups.push({ ...replacement, exists, backup });
    }
    for (const replacement of replacements) {
      await rename(replacement.replacement, replacement.target);
      committed.push(replacement.target);
    }
  } catch (error) {
    for (const target of committed.reverse()) {
      const backup = backups.find((item) => item.target === target);
      if (backup?.exists) await rename(backup.backup, target).catch(() => {});
      else await rm(target, { force: true }).catch(() => {});
    }
    throw error;
  } finally {
    await Promise.all(backups.map((item) => rm(item.backup, { force: true })));
    await Promise.all(replacements.map((item) => rm(item.replacement, { force: true })));
  }
}

async function generate(workbook, plan, dryRun, requestedBackend) {
  const label = `Audio plan ${plan.id}`;
  const audioPlan = plan.audio;
  const voices = validateAudioPlan(audioPlan, label);
  if (requestedBackend && requestedBackend !== audioPlan.backend) {
    fail(`${label} declares ${audioPlan.backend}; update its explicit backend plan before generating with ${requestedBackend}`);
  }
  if (workbook.audio !== undefined && !sameAudioIdentity(workbook.audio, audioPlan)) fail(`${label}: declared audio provenance must exactly match prompts/audio-pilot.json`);
  if (!Array.isArray(plan.segments) || plan.segments.length === 0) fail(`${label}.segments must be a non-empty array`);
  plan.segments.forEach((segment, index) => {
    if (!segment || typeof segment.role !== "string" || typeof segment.text !== "string" || segment.text.trim() === "") fail(`${label}.segments[${index}] requires role and text`);
    if (!voices.has(segment.role)) fail(`${label}.segments[${index}] references unknown role ${segment.role}`);
  });
  assertPlanMatchesWorkbookText(workbook, plan, label);
  const audioTarget = toPublicFile(audioPlan.path);
  const transcriptTarget = toPublicFile(audioPlan.transcriptPath);
  const manifestTarget = toPublicFile(audioPlan.metadataPath);
  if (dryRun) {
    console.log(`Audio plan valid: ${workbook.id} → ${audioPlan.path}${workbook.audio ? " (metadata matches)" : " (metadata pending local output)"}`);
    return;
  }
  const tempDir = await mkdtemp(path.join(os.tmpdir(), "worksheet-audio-"));
  try {
    const synthesized = audioPlan.backend === "kokoro"
      ? await runKokoro(tempDir, plan, audioPlan, voices)
      : await runOpenAi(tempDir, plan, audioPlan, voices);
    if (!(await fileExists(synthesized.candidate))) fail(`${label}: synthesis did not create an MP3 candidate`);
    const integrity = await probeAudio(synthesized.candidate);
    const audio = finalAudioMetadata(audioPlan, integrity);
    const manifest = {
      schemaVersion: 1,
      workbookId: workbook.id,
      aiGenerated: true,
      disclosure: audio.disclosure,
      backend: audio.backend,
      model: audio.model,
      modelRevision: audio.modelRevision,
      modelSha256: audio.modelSha256,
      license: audio.license,
      voices: audio.voices,
      audio: { path: audio.path, sha256: audio.sha256, durationSeconds: audio.durationSeconds, sampleRate: 24000, codec: "mp3" },
      transcriptPath: audio.transcriptPath,
      synthesis: synthesized.provenance,
    };
    await Promise.all([mkdir(path.dirname(audioTarget), { recursive: true }), mkdir(path.dirname(transcriptTarget), { recursive: true }), mkdir(path.dirname(manifestTarget), { recursive: true })]);
    const suffix = `.replacement-${process.pid}-${Date.now()}`;
    const audioReplacement = `${audioTarget}${suffix}`;
    const transcriptReplacement = `${transcriptTarget}${suffix}`;
    const manifestReplacement = `${manifestTarget}${suffix}`;
    await Promise.all([
      copyFile(synthesized.candidate, audioReplacement),
      writeFile(transcriptReplacement, transcriptHtml(workbook, plan, audio), "utf8"),
      writeFile(manifestReplacement, `${JSON.stringify(manifest, null, 2)}\n`, "utf8"),
    ]);
    const stagedIntegrity = await probeAudio(audioReplacement);
    if (stagedIntegrity.sha256 !== audio.sha256 || stagedIntegrity.durationSeconds !== audio.durationSeconds) fail(`${label}: staged MP3 integrity changed before promotion`);
    const metadataReplacements = await stageContentMetadata(workbook, audio);
    await commitTransaction([
      { target: audioTarget, replacement: audioReplacement },
      { target: transcriptTarget, replacement: transcriptReplacement },
      { target: manifestTarget, replacement: manifestReplacement },
      ...metadataReplacements,
    ]);
    console.log(`Generated ${audio.path} (${audio.durationSeconds}s, ${audio.sha256}) with ${audio.backend}; synchronized transcript, manifest, and catalog.`);
  } finally {
    await rm(tempDir, { recursive: true, force: true });
  }
}

async function main() {
  const { ids, dryRun, backend } = parseArgs(process.argv.slice(2));
  const [config, { workbooks }] = await Promise.all([readFile(configPath, "utf8").then(JSON.parse), loadAndValidateContent()]);
  if (!config || config.version !== 2 || config.defaultBackend !== "kokoro" || !Array.isArray(config.workbooks)) {
    fail("prompts/audio-pilot.json must be a version 2 plan with Kokoro as defaultBackend");
  }
  const plans = config.workbooks.filter((plan) => ids.size === 0 || ids.has(plan.id));
  if (ids.size && plans.length !== ids.size) fail(`No audio plan for: ${[...ids].filter((id) => !plans.some((plan) => plan.id === id)).join(", ")}`);
  for (const plan of plans) {
    const workbook = workbooks.find((item) => item.id === plan.id);
    if (!workbook) fail(`Audio plan references unknown workbook: ${plan.id}`);
    await generate(workbook, plan, dryRun, backend);
  }
}

main().catch((error) => { console.error(`Audio generation failed: ${error.message}`); process.exitCode = 1; });
