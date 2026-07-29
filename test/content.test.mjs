import test from "node:test";
import assert from "node:assert/strict";
import { loadAndValidateContent, validateWorkbook } from "../scripts/validate-content.mjs";

test("published collections cover all mathematics, English, and Korean standards", async () => {
  const { catalog, workbooks } = await loadAndValidateContent();
  const math = workbooks.filter(({ subject }) => subject === "math");
  const english = workbooks.filter(({ subject }) => subject === "english");
  const korean = workbooks.filter(({ subject }) => subject === "korean");
  assert.equal(catalog.version, 2);
  assert.equal(math.length, 53);
  assert.equal(english.length, 16);
  assert.equal(korean.length, 18);
  assert.equal(new Set(math.flatMap(({ standardCodes }) => standardCodes)).size, 121);
  assert.equal(new Set(english.flatMap(({ standardCodes }) => standardCodes)).size, 40);
  assert.equal(new Set(korean.flatMap(({ standardCodes }) => standardCodes)).size, 87);
  const koreanRanges = [[2, 1, 5], [2, 2, 5], [2, 3, 4], [2, 4, 3], [2, 5, 4], [2, 6, 2], [4, 1, 6], [4, 2, 6], [4, 3, 5], [4, 4, 5], [4, 5, 5], [4, 6, 3], [6, 1, 7], [6, 2, 5], [6, 3, 6], [6, 4, 6], [6, 5, 6], [6, 6, 4]];
  const expectedKoreanCodes = koreanRanges.flatMap(([band, area, count]) =>
    Array.from({ length: count }, (_, index) => `[${band}국${String(area).padStart(2, "0")}-${String(index + 1).padStart(2, "0")}]`)
  );
  assert.deepEqual([...new Set(korean.flatMap(({ standardCodes }) => standardCodes))].sort(), expectedKoreanCodes.sort());
  const expectedEnglishCodes = [
    ...Array.from({ length: 10 }, (_, index) => `[4영01-${String(index + 1).padStart(2, "0")}]`),
    ...Array.from({ length: 10 }, (_, index) => `[4영02-${String(index + 1).padStart(2, "0")}]`),
    ...Array.from({ length: 10 }, (_, index) => `[6영01-${String(index + 1).padStart(2, "0")}]`),
    ...Array.from({ length: 10 }, (_, index) => `[6영02-${String(index + 1).padStart(2, "0")}]`),
  ];
  assert.deepEqual([...new Set(english.flatMap(({ standardCodes }) => standardCodes))].sort(), expectedEnglishCodes.sort());
  assert.equal(english.flatMap(({ pages }) => pages).length, 96);
  assert.equal(korean.flatMap(({ pages }) => pages).length, 144);
  assert.deepEqual(new Set(english.map(({ gradeBand }) => gradeBand)), new Set(["3-4", "5-6"]));
  assert.deepEqual(new Set(korean.map(({ gradeBand }) => gradeBand)), new Set(["1-2", "3-4", "5-6"]));
  for (const band of ["1-2", "3-4", "5-6"]) {
    assert.deepEqual(new Set(korean.filter(({ gradeBand }) => gradeBand === band).map(({ domain }) => domain)), new Set(["듣기·말하기", "읽기", "쓰기", "문법", "문학", "매체"]));
  }

  for (const workbook of workbooks) {
    const levels = workbook.subject === "math" ? ["foundation", "standard", "challenge"] : workbook.subject === "english" ? ["input", "practice", "production"] : ["read", "explore", "express"];
    assert.deepEqual(workbook.levels, levels);
    assert.equal(workbook.license, "CC-BY-NC-SA-4.0");
    assert.equal(workbook.author, "Taehyeong Lim");
    assert.equal(workbook.standardCodes.length > 0, true);
    assert.equal(workbook.pages.length, workbook.subject === "math" ? 4 : workbook.subject === "english" ? 6 : 8);
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

function pilotWorkbook() {
  return {
    id: "english-3-4-story-listening", slug: "english-3-4-story-listening", subject: "english", title: "pilot", gradeBand: "3-4", domain: "듣기", module: "pilot",
    standardCodes: ["[4영01-01]"], levels: ["input", "practice", "production"],
    activities: { words: [["hello", "안녕"]], text: ["Hello."], practice: [["hello를 고르세요.", "hello"]], check: [["인사말을 쓰세요.", "hello"]], produce: ["인사하기"], model: "Hello." },
    qualityProfile: "pilot-v1",
    activityEvidence: [{ id: "word-check", activityKey: "words", promptIndex: 0, standardCodes: ["[4영01-01]"], evidenceType: "selected-response", expectedResponse: "hello를 고른다.", scoringRubric: { needsSupport: "도움이 필요하다.", meets: "알맞게 고른다.", exceeds: "이유를 설명한다." } }],
    studentSelfCheck: [
      { id: "check-one", label: "낱말을 찾을 수 있어요.", standardCodes: ["[4영01-01]"] },
      { id: "check-two", label: "답을 말할 수 있어요.", standardCodes: ["[4영01-01]"] },
      { id: "check-three", label: "스스로 확인할 수 있어요.", standardCodes: ["[4영01-01]"] },
    ],
    teacherRubric: {
      disclaimer: "수업 중 관찰과 피드백을 위한 기준입니다.",
      levels: [
        { id: "needs-support", label: "도움 필요", descriptor: "도움을 받아 수행한다." },
        { id: "meets", label: "도달", descriptor: "핵심 수행을 해낸다." },
        { id: "exceeds", label: "확장", descriptor: "근거를 더해 수행한다." },
      ],
      criteria: [{ id: "word-use", label: "낱말을 이해한다.", standardCodes: ["[4영01-01]"], evidenceActivityIds: ["word-check"] }],
    },
    pages: [
      { id: "cover", order: 1, role: "cover", imagePath: "/workbooks/english-3-4-story-listening/cover.webp", thumbnailPath: "/workbooks/english-3-4-story-listening/cover.webp", sha256: "a".repeat(64), alt: "cover", approved: true },
      { id: "input", order: 2, role: "worksheet", imagePath: "/workbooks/english-3-4-story-listening/input.webp", thumbnailPath: "/workbooks/english-3-4-story-listening/input.webp", sha256: "a".repeat(64), alt: "input", approved: true },
      { id: "answers", order: 3, role: "answer", imagePath: "/workbooks/english-3-4-story-listening/answers.webp", thumbnailPath: "/workbooks/english-3-4-story-listening/answers.webp", sha256: "a".repeat(64), alt: "answers", approved: true },
    ],
    pdf: { path: "/workbooks/english-3-4-story-listening/pilot.pdf", pageCount: 3, sha256: "a".repeat(64) }, transcriptPath: "/workbooks/english-3-4-story-listening/transcript.html",
    license: "CC-BY-NC-SA-4.0", author: "Taehyeong Lim", publishedAt: "2026-07-29", published: true,
  };
}

test("pilot quality metadata cross-references activities, standards, and rubric evidence", () => {
  const workbook = pilotWorkbook();
  assert.doesNotThrow(() => validateWorkbook(workbook, "pilot"));

  workbook.activityEvidence[0].standardCodes = ["[4영01-02]"];
  assert.throws(() => validateWorkbook(workbook, "pilot"), /must belong to the workbook standardCodes/);
});

test("declared audio records pinned Kokoro provenance and complete output metadata", () => {
  const workbook = pilotWorkbook();
  workbook.audio = {
    path: "/workbooks/english-3-4-story-listening/listening.mp3",
    transcriptPath: "/workbooks/english-3-4-story-listening/listening.vtt",
    metadataPath: "/workbooks/english-3-4-story-listening/listening.metadata.json",
    aiGenerated: true,
    backend: "kokoro",
    model: "hexgrad/Kokoro-82M",
    modelRevision: "f3ff3571791e39611d31c381e3a41a3af07b4987",
    modelSha256: "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4",
    license: "Apache-2.0",
    disclosure: "AI 생성 음성입니다.",
    voices: [{ role: "narrator", voice: "af_bella", locale: "en-US", sha256: "8cb64e02fcc8de0327a8e13817e49c76c945ecf0052ceac97d3081480e8e48d6" }],
    playbackRates: [0.75, 1],
    durationSeconds: 2.5,
    sha256: "a".repeat(64),
  };
  assert.doesNotThrow(() => validateWorkbook(workbook, "pilot"));
  workbook.audio.modelRevision = "main";
  assert.throws(() => validateWorkbook(workbook, "pilot"), /Kokoro provenance/);

  workbook.audio = {
    ...workbook.audio,
    backend: "openai",
    model: "gpt-4o-mini-tts-2025-12-15",
    modelRevision: "2025-12-15",
    modelSha256: null,
    license: "OpenAI Terms of Use",
    voices: [{ role: "narrator", voice: "cedar", locale: "en-US", sha256: null }],
  };
  assert.doesNotThrow(() => validateWorkbook(workbook, "pilot"));
});
