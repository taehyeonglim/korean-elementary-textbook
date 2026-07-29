import test from "node:test";
import assert from "node:assert/strict";
import { loadAndValidateContent, validateWorkbook } from "../scripts/validate-content.mjs";

test("53 curriculum-linked workbooks cover 121 standards with 212 published WebP pages", async () => {
  const { catalog, workbooks } = await loadAndValidateContent();
  assert.equal(catalog.version, 1);
  assert.equal(workbooks.length, 53);
  assert.equal(new Set(workbooks.flatMap(({ standardCodes }) => standardCodes)).size, 121);
  assert.equal(workbooks.flatMap(({ pages }) => pages).length, 212);
  assert.deepEqual(new Set(workbooks.map(({ gradeBand }) => gradeBand)), new Set(["1-2", "3-4", "5-6"]));

  for (const workbook of workbooks) {
    assert.deepEqual(workbook.levels, ["foundation", "standard", "challenge"]);
    assert.equal(workbook.license, "CC-BY-NC-SA-4.0");
    assert.equal(workbook.author, "Taehyeong Lim");
    assert.equal(workbook.standardCodes.length > 0, true);
    assert.equal(workbook.pages.length, 4);
    assert.deepEqual(workbook.pages.map(({ role }) => role), ["cover", "worksheet", "worksheet", "answer"]);
    assert.equal(workbook.pdf.pageCount, workbook.pages.length);
    assert.equal(workbook.published, true);
    assert.equal(workbook.pages.every(({ approved }) => approved), true);
    assert.equal(workbook.pages.every(({ imagePath, thumbnailPath }) => imagePath === thumbnailPath && imagePath.endsWith(".webp")), true);
  }
});

test("published workbooks require approved pages", () => {
  assert.throws(() => validateWorkbook({
    id: "test-book", slug: "test-book", title: "test", gradeBand: "1-2", domain: "수와 연산", module: "test",
    standardCodes: ["[2수01-05]"], levels: ["foundation", "standard", "challenge"],
    pages: [{ id: "cover", order: 1, role: "cover", imagePath: "/workbooks/test-book/cover.png", thumbnailPath: "/workbooks/test-book/cover.webp", sha256: "a".repeat(64), alt: "test", approved: false }],
    pdf: { path: "/workbooks/test-book/book.pdf", pageCount: 1, sha256: "a".repeat(64) }, transcriptPath: "/workbooks/test-book/transcript.html",
    license: "CC-BY-NC-SA-4.0", author: "Taehyeong Lim", publishedAt: "2026-07-28", published: true,
  }, "test"), /cannot be published/);
});
