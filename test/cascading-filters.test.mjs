import test from "node:test";
import assert from "node:assert/strict";
import { availableValuesFromUpstream, matchesFilters, normalizeFilters } from "../src/scripts/cascading-filters.js";

const fields = ["gradeBand", "domain", "module"];
const records = [
  { gradeBand: "1-2", domain: "수와 연산", module: "덧셈" },
  { gradeBand: "1-2", domain: "측정", module: "길이" },
  { gradeBand: "3-4", domain: "수와 연산", module: "나눗셈" },
];

test("cascading options only include values that can produce a result with broader selections", () => {
  const values = { gradeBand: "1-2", domain: "수와 연산", module: "" };
  assert.deepEqual(
    [...availableValuesFromUpstream(records, values, "module", fields)].sort(),
    ["덧셈"],
  );
  assert.equal(matchesFilters(records[0], values, fields), true);
  assert.equal(matchesFilters(records[1], values, fields), false);
});

test("a lower selection never hides broader grade or domain options", () => {
  const values = { gradeBand: "1-2", domain: "", module: "길이" };
  assert.deepEqual(
    [...availableValuesFromUpstream(records, values, "gradeBand", fields)].sort(),
    ["1-2", "3-4"],
  );
  assert.deepEqual(
    [...availableValuesFromUpstream(records, values, "domain", fields)].sort(),
    ["수와 연산", "측정"],
  );
});

test("an upstream change clears dependent selections that no longer have a result", () => {
  const values = normalizeFilters(records, {
    gradeBand: "3-4",
    domain: "측정",
    module: "길이",
  }, fields);
  assert.deepEqual(values, { gradeBand: "3-4", domain: "", module: "" });
});

test("a new domain selection is preserved and clears an incompatible older module", () => {
  const values = normalizeFilters(records, {
    gradeBand: "1-2",
    domain: "수와 연산",
    module: "길이",
  }, fields);
  assert.deepEqual(values, { gradeBand: "1-2", domain: "수와 연산", module: "" });
});
