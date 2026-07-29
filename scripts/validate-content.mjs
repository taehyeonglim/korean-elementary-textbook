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
const ENGLISH_STAGES = ["input", "practice", "production"];
const KOREAN_STAGES = ["read", "explore", "express"];
const ROLES = new Set(["cover", "worksheet", "answer"]);
const GRADE_BANDS = new Set(["1-2", "3-4", "5-6"]);
const SUBJECTS = new Set(["math", "english", "korean"]);
const SUBJECT_CODE_MARKERS = { math: "수", english: "영", korean: "국" };
const SUBJECT_GRADE_BANDS = {
  math: new Set(["1-2", "3-4", "5-6"]),
  english: new Set(["3-4", "5-6"]),
  korean: new Set(["1-2", "3-4", "5-6"]),
};
const PILOT_QUALITY_PROFILE = "pilot-v1";
const PILOT_WORKBOOK_IDS = new Set([
  "english-3-4-story-listening",
  "english-5-6-stories-culture-team",
  "korean-1-2-listening-speaking",
  "korean-3-4-writing",
  "korean-5-6-reading",
]);
const QUALITY_ID = /^[a-z0-9][a-z0-9-]{1,63}$/;
const AUDIO_PATH = /^\/workbooks\/[a-z0-9][a-z0-9/_-]*\.(?:mp3|m4a|wav|ogg)$/;
const AUDIO_TRANSCRIPT_PATH = /^\/workbooks\/[a-z0-9][a-z0-9/_-]*\.(?:html|txt|vtt)$/;
const AUDIO_METADATA_PATH = /^\/workbooks\/[a-z0-9][a-z0-9/_.-]*\.json$/;
const RUBRIC_LEVEL_IDS = ["needs-support", "meets", "exceeds"];
const KOKORO_MODEL = "hexgrad/Kokoro-82M";
const KOKORO_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987";
const KOKORO_MODEL_SHA256 = "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4";

function assertCodeList(value, label, workbookCodes) {
  if (!Array.isArray(value) || value.length === 0) fail(`${label} must be a non-empty array`);
  const codes = new Set();
  value.forEach((code, index) => {
    assertString(code, `${label}[${index}]`, { pattern: STANDARD_CODE });
    if (codes.has(code)) fail(`${label} contains duplicate standard code: ${code}`);
    codes.add(code);
    if (workbookCodes && !workbookCodes.has(code)) fail(`${label}[${index}] must belong to the workbook standardCodes`);
  });
}

function assertUniqueIds(entries, label) {
  const ids = new Set();
  entries.forEach((entry, index) => {
    if (!isPlainObject(entry)) fail(`${label}[${index}] must be an object`);
    assertString(entry.id, `${label}[${index}].id`, { pattern: QUALITY_ID });
    if (ids.has(entry.id)) fail(`${label} contains duplicate id: ${entry.id}`);
    ids.add(entry.id);
  });
  return ids;
}

function assertOnlyKeys(value, label, allowedKeys) {
  for (const key of Object.keys(value)) {
    if (!allowedKeys.has(key)) fail(`${label} has an unsupported property: ${key}`);
  }
}

function validateAudio(audio, label) {
  if (!isPlainObject(audio)) fail(`${label}.audio must be an object when declared`);
  assertOnlyKeys(audio, `${label}.audio`, new Set(["path", "transcriptPath", "metadataPath", "aiGenerated", "backend", "model", "modelRevision", "modelSha256", "license", "disclosure", "voices", "playbackRates", "durationSeconds", "sha256"]));
  assertString(audio.path, `${label}.audio.path`, { pattern: AUDIO_PATH });
  assertString(audio.transcriptPath, `${label}.audio.transcriptPath`, { pattern: AUDIO_TRANSCRIPT_PATH });
  assertString(audio.metadataPath, `${label}.audio.metadataPath`, { pattern: AUDIO_METADATA_PATH });
  if (typeof audio.aiGenerated !== "boolean") fail(`${label}.audio.aiGenerated must be boolean`);
  if (!new Set(["kokoro", "openai"]).has(audio.backend)) fail(`${label}.audio.backend must be kokoro or openai`);
  for (const key of ["model", "modelRevision", "license", "disclosure"]) assertString(audio[key], `${label}.audio.${key}`);
  if (audio.modelSha256 !== null && !SHA256.test(audio.modelSha256)) fail(`${label}.audio.modelSha256 must be a SHA-256 or null`);
  if (audio.backend === "kokoro" && (audio.model !== KOKORO_MODEL || audio.modelRevision !== KOKORO_REVISION || audio.modelSha256 !== KOKORO_MODEL_SHA256 || audio.license !== "Apache-2.0")) {
    fail(`${label}.audio Kokoro provenance must use the pinned official model, revision, SHA-256, and Apache-2.0 license`);
  }
  if (!Array.isArray(audio.voices) || audio.voices.length === 0) fail(`${label}.audio.voices must be a non-empty array`);
  const roles = new Set();
  audio.voices.forEach((voice, index) => {
    if (!isPlainObject(voice)) fail(`${label}.audio.voices[${index}] must be an object`);
    assertOnlyKeys(voice, `${label}.audio.voices[${index}]`, new Set(["role", "voice", "locale", "sha256"]));
    assertString(voice.role, `${label}.audio.voices[${index}].role`);
    assertString(voice.voice, `${label}.audio.voices[${index}].voice`);
    if (roles.has(voice.role)) fail(`${label}.audio.voices has duplicate role ${voice.role}`);
    roles.add(voice.role);
    if (voice.locale !== "en-US") fail(`${label}.audio.voices[${index}].locale must be en-US`);
    if (voice.sha256 !== null && !SHA256.test(voice.sha256)) fail(`${label}.audio.voices[${index}].sha256 must be a SHA-256 or null`);
  });
  if (!Array.isArray(audio.playbackRates) || audio.playbackRates.length === 0) fail(`${label}.audio.playbackRates must be a non-empty array`);
  audio.playbackRates.forEach((rate, index) => {
    if (typeof rate !== "number" || !Number.isFinite(rate) || rate <= 0 || rate > 4) {
      fail(`${label}.audio.playbackRates[${index}] must be a number greater than 0 and no more than 4`);
    }
  });
  if (typeof audio.durationSeconds !== "number" || !Number.isFinite(audio.durationSeconds) || audio.durationSeconds <= 0) fail(`${label}.audio.durationSeconds must be a positive number`);
  if (!SHA256.test(audio.sha256)) fail(`${label}.audio.sha256 must be a SHA-256`);
}

function validatePilotQuality(workbook, label) {
  if (workbook.qualityProfile === undefined) return;
  if (workbook.qualityProfile !== PILOT_QUALITY_PROFILE) fail(`${label}.qualityProfile must be ${PILOT_QUALITY_PROFILE}`);
  if (!PILOT_WORKBOOK_IDS.has(workbook.id)) fail(`${label}.qualityProfile is only available for the approved pilot workbooks`);

  const workbookCodes = new Set(workbook.standardCodes);
  if (!Array.isArray(workbook.activityEvidence) || workbook.activityEvidence.length === 0) fail(`${label}.activityEvidence must be a non-empty array for ${PILOT_QUALITY_PROFILE}`);
  const evidenceIds = assertUniqueIds(workbook.activityEvidence, `${label}.activityEvidence`);
  const coveredCodes = new Set();
  for (const [index, evidence] of workbook.activityEvidence.entries()) {
    const evidenceLabel = `${label}.activityEvidence[${index}]`;
    assertOnlyKeys(evidence, evidenceLabel, new Set(["id", "activityKey", "promptIndex", "standardCodes", "evidenceType", "expectedResponse", "scoringRubric"]));
    assertString(evidence.activityKey, `${evidenceLabel}.activityKey`);
    const activity = workbook.activities[evidence.activityKey];
    if (activity === undefined || evidence.activityKey === "model") fail(`${evidenceLabel}.activityKey must name a student activity`);
    if (evidence.promptIndex !== undefined) {
      if (!Number.isInteger(evidence.promptIndex) || evidence.promptIndex < 0) fail(`${evidenceLabel}.promptIndex must be a non-negative integer`);
      if (!Array.isArray(activity) || evidence.promptIndex >= activity.length) fail(`${evidenceLabel}.promptIndex must point to an item in activities.${evidence.activityKey}`);
    }
    assertCodeList(evidence.standardCodes, `${evidenceLabel}.standardCodes`, workbookCodes);
    evidence.standardCodes.forEach((code) => coveredCodes.add(code));
    assertString(evidence.evidenceType, `${evidenceLabel}.evidenceType`);
    assertString(evidence.expectedResponse, `${evidenceLabel}.expectedResponse`);
    if (!isPlainObject(evidence.scoringRubric)) fail(`${evidenceLabel}.scoringRubric must be an object`);
    assertOnlyKeys(evidence.scoringRubric, `${evidenceLabel}.scoringRubric`, new Set(["needsSupport", "meets", "exceeds"]));
    for (const key of ["needsSupport", "meets", "exceeds"]) assertString(evidence.scoringRubric[key], `${evidenceLabel}.scoringRubric.${key}`);
  }
  for (const code of workbook.standardCodes) {
    if (!coveredCodes.has(code)) fail(`${label}.activityEvidence must cover workbook standard code ${code}`);
  }

  if (!Array.isArray(workbook.studentSelfCheck) || workbook.studentSelfCheck.length !== 3) fail(`${label}.studentSelfCheck must contain exactly three checks`);
  assertUniqueIds(workbook.studentSelfCheck, `${label}.studentSelfCheck`);
  workbook.studentSelfCheck.forEach((check, index) => {
    const checkLabel = `${label}.studentSelfCheck[${index}]`;
    assertOnlyKeys(check, checkLabel, new Set(["id", "label", "standardCodes"]));
    assertString(check.label, `${checkLabel}.label`);
    assertCodeList(check.standardCodes, `${checkLabel}.standardCodes`, workbookCodes);
  });

  if (!isPlainObject(workbook.teacherRubric)) fail(`${label}.teacherRubric must be an object`);
  assertOnlyKeys(workbook.teacherRubric, `${label}.teacherRubric`, new Set(["disclaimer", "levels", "criteria"]));
  assertString(workbook.teacherRubric.disclaimer, `${label}.teacherRubric.disclaimer`);
  const { levels, criteria } = workbook.teacherRubric;
  if (!Array.isArray(levels) || levels.length !== 3) fail(`${label}.teacherRubric.levels must contain exactly three levels`);
  const levelIds = assertUniqueIds(levels, `${label}.teacherRubric.levels`);
  if (JSON.stringify([...levelIds].sort()) !== JSON.stringify([...RUBRIC_LEVEL_IDS].sort())) fail(`${label}.teacherRubric.levels must use needs-support, meets, and exceeds`);
  levels.forEach((level, index) => {
    assertOnlyKeys(level, `${label}.teacherRubric.levels[${index}]`, new Set(["id", "label", "descriptor"]));
    assertString(level.label, `${label}.teacherRubric.levels[${index}].label`);
    assertString(level.descriptor, `${label}.teacherRubric.levels[${index}].descriptor`);
  });
  if (!Array.isArray(criteria) || criteria.length === 0) fail(`${label}.teacherRubric.criteria must be a non-empty array`);
  assertUniqueIds(criteria, `${label}.teacherRubric.criteria`);
  criteria.forEach((criterion, index) => {
    const criterionLabel = `${label}.teacherRubric.criteria[${index}]`;
    assertOnlyKeys(criterion, criterionLabel, new Set(["id", "label", "standardCodes", "evidenceActivityIds"]));
    assertString(criterion.label, `${criterionLabel}.label`);
    assertCodeList(criterion.standardCodes, `${criterionLabel}.standardCodes`, workbookCodes);
    if (!Array.isArray(criterion.evidenceActivityIds) || criterion.evidenceActivityIds.length === 0) fail(`${criterionLabel}.evidenceActivityIds must be a non-empty array`);
    criterion.evidenceActivityIds.forEach((evidenceId, evidenceIndex) => {
      assertString(evidenceId, `${criterionLabel}.evidenceActivityIds[${evidenceIndex}]`, { pattern: QUALITY_ID });
      if (!evidenceIds.has(evidenceId)) fail(`${criterionLabel}.evidenceActivityIds[${evidenceIndex}] must reference activityEvidence`);
    });
  });
}

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
  for (const key of ["id", "slug", "subject", "title", "domain", "module", "author", "publishedAt", "transcriptPath"]) {
    assertString(workbook[key], `${label}.${key}`);
  }
  for (const key of ["id", "slug"]) assertString(workbook[key], `${label}.${key}`, { pattern: ID });
  if (!SUBJECTS.has(workbook.subject)) fail(`${label}.subject must be math, english, or korean`);
  if (!GRADE_BANDS.has(workbook.gradeBand)) fail(`${label}.gradeBand must be 1-2, 3-4, or 5-6`);
  if (!SUBJECT_GRADE_BANDS[workbook.subject].has(workbook.gradeBand)) fail(`${label}.gradeBand is not available for ${workbook.subject}`);
  if (workbook.grade !== undefined && ![1, 2, 3, 4, 5, 6].includes(workbook.grade)) fail(`${label}.grade must be 1–6 when supplied`);
  if (!Array.isArray(workbook.standardCodes) || workbook.standardCodes.length === 0) fail(`${label}.standardCodes must not be empty`);
  workbook.standardCodes.forEach((code, index) => assertString(code, `${label}.standardCodes[${index}]`, { pattern: STANDARD_CODE }));
  if (new Set(workbook.standardCodes).size !== workbook.standardCodes.length) fail(`${label}.standardCodes must not contain duplicates`);
  if (workbook.standardCodes.some((code) => !code.includes(SUBJECT_CODE_MARKERS[workbook.subject]))) {
    fail(`${label}.standardCodes must match subject ${workbook.subject}`);
  }
  const expectedStages = workbook.subject === "math" ? LEVELS : workbook.subject === "english" ? ENGLISH_STAGES : KOREAN_STAGES;
  if (JSON.stringify(workbook.levels) !== JSON.stringify(expectedStages)) fail(`${label}.levels must match the subject learning flow`);
  if (workbook.subject === "english") {
    if (!isPlainObject(workbook.activities)) fail(`${label}.activities must describe the English input, practice, and production flow`);
    for (const key of ["words", "text", "practice", "check", "produce"]) {
      if (!Array.isArray(workbook.activities[key]) || workbook.activities[key].length === 0) fail(`${label}.activities.${key} must not be empty`);
    }
    assertString(workbook.activities.model, `${label}.activities.model`);
  }
  if (workbook.subject === "korean") {
    if (!isPlainObject(workbook.activities)) fail(`${label}.activities must describe the Korean read, explore, and express flow`);
    for (const key of ["textA", "questionsA", "textB", "questionsB", "focus", "produce"]) {
      if (!Array.isArray(workbook.activities[key]) || workbook.activities[key].length === 0) fail(`${label}.activities.${key} must not be empty`);
    }
    assertString(workbook.activities.model, `${label}.activities.model`);
  }
  if (workbook.audio !== undefined) validateAudio(workbook.audio, label);
  validatePilotQuality(workbook, label);
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
  if (!isPlainObject(catalog) || catalog.version !== 2 || !Array.isArray(catalog.workbooks)) fail("content/catalog.json must be a version 2 catalog with a workbooks array");
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
