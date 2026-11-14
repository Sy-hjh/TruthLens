import assert from "node:assert/strict";
import { moduleSignal } from "./src/signals.ts";
assert.equal(moduleSignal({ status: "completed", score: 1 }).level, "alert");
assert.equal(
  moduleSignal({ status: "completed", segments: [{ start: 0, score: 0.739 }] })
    .level,
  "alert",
);
assert.equal(
  moduleSignal({ status: "completed", score: 0.2 }).level,
  "uncertain",
);
assert.equal(
  moduleSignal({ status: "failed", score: 0.99 }).level,
  "unavailable",
);
assert.equal(
  moduleSignal({ status: "completed", score: 0.6, threshold: 0.7 }).level,
  "uncertain",
);
assert.equal(
  moduleSignal({
    status: "completed",
    segments: [
      { start: 0, score: 0.1 },
      { start: 5, score: 0.8 },
    ],
  }).flagged,
  1,
);
assert.equal(
  moduleSignal({ status: "completed", segments: [] }).level,
  "unavailable",
);
assert.equal(
  moduleSignal({
    status: "completed",
    score: 0.018737,
    threshold: 0.5,
    sensitivity_threshold: 0.007,
  }).level,
  "uncertain",
);
assert.equal(
  moduleSignal({
    status: "completed",
    score: 0.99784,
    threshold: 0.5,
    sensitivity_threshold: 0.007,
  }).level,
  "alert",
);
console.log("9 signal threshold checks passed");
