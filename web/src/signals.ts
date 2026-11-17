import type { ModuleResult } from "./api";
export type SignalLevel = "alert" | "uncertain" | "unavailable";
export function moduleSignal(m: ModuleResult) {
  const values =
    m.segments?.map((s) => ({
      score: s.score,
      threshold: s.threshold ?? 0.5,
      start: s.start,
    })) || [];
  if (m.score !== undefined)
    values.push({ score: m.score, threshold: m.threshold ?? 0.5, start: 0 });
  if (m.status === "completed" && m.method === "fused") {
    const count = m.regions?.length ?? 0;
    return {
      level: (count ? "alert" : "uncertain") as SignalLevel,
      title: count ? "有异常" : "未发现明显异常",
      score: null,
      flagged: count,
      total: count,
    };
  }
  if (m.status !== "completed" || !values.length)
    return {
      level: "unavailable" as SignalLevel,
      title: "这一项暂时无法判断",
      score: null,
      flagged: 0,
      total: 0,
    };
  const flagged = values.filter((v) => v.score >= v.threshold).length;
  const localWarning = !!m.regions?.length;
  const score = Math.max(...values.map((v) => v.score));
  return {
    level: (flagged || localWarning ? "alert" : "uncertain") as SignalLevel,
    title: localWarning ? "发现局部异常区域" : flagged ? "发现合成线索" : "还不能确认真假",
    score,
    flagged,
    total: values.length,
  };
}
