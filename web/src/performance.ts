import { onCLS, onINP, onLCP, onFCP, onTTFB } from "web-vitals";
import type { Metric } from "web-vitals";

// Local-only, content-free diagnostics for repeatable frontend acceptance.
// No analytics endpoint, user identifier, contact or media is collected.
const meta = document.createElement("meta");
meta.name = "truthlens-vitals";
document.head.append(meta);
const values: Record<string, { value: number; rating: string; unit: string }> =
  {};
const publish = () => {
  meta.content = JSON.stringify({
    scope: "current browser page, local only; not population field data",
    viewport: [innerWidth, innerHeight],
    values,
  });
};
function record(m: Metric) {
  values[m.name] = {
    value: Number(m.value.toFixed(4)),
    rating: m.rating,
    unit: m.name === "CLS" ? "score" : "ms",
  };
  publish();
}
publish();
onCLS(record, { reportAllChanges: true });
onINP(record, { reportAllChanges: true });
onLCP(record, { reportAllChanges: true });
onFCP(record, { reportAllChanges: true });
onTTFB(record, { reportAllChanges: true });
