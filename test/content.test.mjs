import test from "node:test";
import assert from "node:assert/strict";
import { loadAndValidateContent, validateWorkbook } from "../scripts/validate-content.mjs";

test("published collections cover all mathematics and English standards", async () => {
  const { catalog, workbooks } = await loadAndValidateContent();
  const math = workbooks.filter(({ subject }) => subject === "math");
  const english = workbooks.filter(({ subject }) => subject === "english");
  assert.equal(catalog.version, 2);
  assert.equal(math.length, 53);
  assert.equal(english.length, 16);
  assert.equal(new Set(math.flatMap(({ standardCodes }) => standardCodes)).size, 121);
  assert.equal(new Set(english.flatMap(({ standardCodes }) => standardCodes)).size, 40);
  const expectedEnglishCodes = [
    ...Array.from({ length: 10 }, (_, index) => `[4영01-${String(index + 1).padStart(2, "0")}]`),
    ...Array.from({ length: 10 }, (_, index) => `[4영02-${String(index + 1).padStart(2, "0")}]`),
    ...Array.from({ length: 10 }, (_, index) => `[6영01-${String(index + 1).padStart(2, "0")}]`),
    ...Array.from({ length: 10 }, (_, index) => `[6영02-${String(index + 1).padStart(2, "0")}]`),
  ];
  assert.deepEqual([...new Set(english.flatMap(({ standardCodes }) => standardCodes))].sort(), expectedEnglishCodes.sort());
  assert.equal(english.flatMap(({ pages }) => pages).length, 96);
  assert.deepEqual(new Set(english.map(({ gradeBand }) => gradeBand)), new Set(["3-4", "5-6"]));

  for (const workbook of workbooks) {
    assert.deepEqual(workbook.levels, workbook.subject === "math" ? ["foundation", "standard", "challenge"] : ["input", "practice", "production"]);
    assert.equal(workbook.license, "CC-BY-NC-SA-4.0");
    assert.equal(workbook.author, "Taehyeong Lim");
    assert.equal(workbook.standardCodes.length > 0, true);
    assert.equal(workbook.pages.length, workbook.subject === "math" ? 4 : 6);
    assert.equal(workbook.pages[0].role, "cover");
    assert.equal(workbook.pages.at(-1).role, "answer");
    assert.equal(workbook.pdf.pageCount, workbook.pages.length);
    assert.equal(workbook.published, true);
    assert.equal(workbook.pages.every(({ approved }) => approved), true);
    assert.equal(workbook.pages.every(({ imagePath, thumbnailPath }) => imagePath === thumbnailPath && imagePath.endsWith(".webp")), true);
  }
});

test("published workbooks require approved pages", () => {
  assert.throws(() => validateWorkbook({
    id: "test-book", slug: "test-book", subject: "math", title: "test", gradeBand: "1-2", domain: "수와 연산", module: "test",
    standardCodes: ["[2수01-05]"], levels: ["foundation", "standard", "challenge"],
    pages: [{ id: "cover", order: 1, role: "cover", imagePath: "/workbooks/test-book/cover.png", thumbnailPath: "/workbooks/test-book/cover.webp", sha256: "a".repeat(64), alt: "test", approved: false }],
    pdf: { path: "/workbooks/test-book/book.pdf", pageCount: 1, sha256: "a".repeat(64) }, transcriptPath: "/workbooks/test-book/transcript.html",
    license: "CC-BY-NC-SA-4.0", author: "Taehyeong Lim", publishedAt: "2026-07-28", published: true,
  }, "test"), /cannot be published/);
});
