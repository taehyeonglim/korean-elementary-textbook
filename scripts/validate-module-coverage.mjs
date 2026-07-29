#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const coverage = JSON.parse(fs.readFileSync(path.join(root, "content/curriculum/module-coverage-2026-07-29.json"), "utf8"));
const workbooks = fs.readdirSync(path.join(root, "content/workbooks"))
  .filter((file) => file.endsWith(".json"))
  .map((file) => JSON.parse(fs.readFileSync(path.join(root, "content/workbooks", file), "utf8")));
const byId = new Map(workbooks.map((workbook) => [workbook.id, workbook]));
const expectedCodes = coverage.modules.flatMap((module) => module.standardCodes);
const seenCodes = new Set();
const errors = [];

for (const module of coverage.modules) {
  const workbook = byId.get(module.workbookId);
  if (!workbook) {
    errors.push(`Missing workbook: ${module.workbookId}`);
    continue;
  }
  if (workbook.questions.length !== 6) errors.push(`${workbook.id}: expected 6 questions`);
  const levels = workbook.questions.map((question) => question.level);
  for (const level of ["foundation", "standard", "challenge"]) {
    if (levels.filter((value) => value === level).length !== 2) errors.push(`${workbook.id}: expected 2 ${level} questions`);
  }
  const primary = new Set(workbook.questions.map((question) => question.standardCode));
  for (const code of module.standardCodes) {
    seenCodes.add(code);
    if (!primary.has(code)) errors.push(`${workbook.id}: no primary question for ${code}`);
  }
  for (const question of workbook.questions) {
    if (!Array.isArray(question.acceptableAnswers) || question.acceptableAnswers.length === 0) errors.push(`${workbook.id}/${question.id}: acceptableAnswers required`);
    if (!question.curriculumBasis?.assessmentPrompt || !question.curriculumBasis?.evidence) errors.push(`${workbook.id}/${question.id}: MCP evidence and assessmentPrompt required`);
  }
}
for (const code of expectedCodes) if (!seenCodes.has(code)) errors.push(`Unassigned standard: ${code}`);
if (coverage.totalModules !== 53 || expectedCodes.length !== 121 || new Set(expectedCodes).size !== 121) errors.push("Coverage manifest invariant failed");
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(JSON.stringify({workbooks: workbooks.length, modules: coverage.totalModules, standards: expectedCodes.length}));
