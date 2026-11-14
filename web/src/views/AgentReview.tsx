import { useEffect, useRef, useState } from "react";
import { api, streamAdvice } from "../api";
import type { Report, AgentAdvice, AgentStep } from "../api";
import { Icon, errorText } from "../ui";
const labels: Record<string, string> = {
  plan: "准备核实",
  read_report: "读取本次报告",
  search_guidance: "查找官方资料",
  read_source: "核对资料来源",
  repair: "重新核对引用",
  output_guard: "校验建议依据",
  fallback_retrieval: "采用有来源的资料建议",
  complete: "核实建议已完成",
};
export default function AgentReview({ report }: { report: Report }) {
  const [question, setQuestion] = useState(""),
    [steps, setSteps] = useState<AgentStep[]>([]),
    [result, setResult] = useState<AgentAdvice | null>(null),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [feedback, setFeedback] = useState(""),
    [feedbackNote, setFeedbackNote] = useState("");
  const controller = useRef<AbortController | null>(null),
    alive = useRef(true);
  const identity =
    report.id + (report.ocr?.text || "") + (report.transcript?.text || "");
  useEffect(() => {
    alive.current = true;
    setResult(null);
    setSteps([]);
    setFeedback("");
    return () => {
      alive.current = false;
      controller.current?.abort();
    };
  }, [identity]);
  async function ask(q: string) {
    if (busy || !q.trim()) return;
    setQuestion(q);
    setBusy(true);
    setError("");
    setSteps([]);
    setResult(null);
    controller.current = new AbortController();
    const timer = setTimeout(() => controller.current?.abort(), 240000);
    try {
      const r = await streamAdvice(
        report.id,
        q.trim(),
        (e) => {
          if (alive.current && e.type === "step") setSteps((s) => [...s, e]);
        },
        controller.current.signal,
      );
      if (alive.current) setResult(r);
    } catch (e) {
      if (alive.current)
        setError(
          e instanceof DOMException && e.name === "AbortError"
            ? "已停止等待。你可以稍后重新提问。"
            : errorText(e),
        );
    } finally {
      clearTimeout(timer);
      if (alive.current) setBusy(false);
    }
  }
  async function rate(verdict: string) {
    try {
      await api("/api/cases/" + report.id + "/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ verdict }),
      });
      setFeedback(verdict);
      setFeedbackNote("反馈已保存，供人工复核，不会直接改变检测结果。");
    } catch (e) {
      setFeedbackNote(errorText(e));
    }
  }
  return (
    <section className="card agent-panel">
      <p className="eyebrow">ASK WITH EVIDENCE / 依据这份报告</p>
      <h2 id="report-question-title" tabIndex={-1}>
        还有疑问？一起核实。
      </h2>
      <p className="muted">结合本次结果和官方资料，帮你找到下一步。</p>
      <div className="agent-prompts">
        {[
          "声音很像，能证明是本人吗？",
          "这份材料有哪些可疑要求？",
          "我现在应该怎么核实？",
        ].map((q) => (
          <button key={q} disabled={busy} onClick={() => void ask(q)}>
            {q}
          </button>
        ))}
      </div>
      <form
        className="agent-form"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
      >
        <input
          aria-label="向真鉴提问"
          placeholder="例如：对方让我保密，我该怎么办？"
          value={question}
          maxLength={200}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={busy}
        />
        <button className="primary" disabled={busy || !question.trim()}>
          {busy ? "正在核实…" : "问问真鉴"}
          <Icon name="arrow" />
        </button>
      </form>
      {busy && (
        <p className="privacy-line" role="status">
          <span className="spinner" />
          正在核实资料，首次加载可能较慢。
          <button className="quiet" onClick={() => controller.current?.abort()}>
            停止等待
          </button>
        </p>
      )}
      {steps.length > 0 && (
        <details className="agent-workflow" open={busy}>
          <summary>
            核实过程 · {busy ? "正在进行" : result ? "已完成" : "未完成"}
          </summary>
          <ol className="agent-trace">
            {steps.map((s, i) => (
              <li key={i}>
                <span>
                  {s.tool === "output_guard" && s.status?.includes("兜底")
                    ? "!"
                    : "✓"}
                </span>
                <div>
                  <b>{labels[s.tool || ""] || "核实步骤"}</b>
                  <small> · {s.status}</small>
                </div>
              </li>
            ))}
          </ol>
        </details>
      )}
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {result && (
        <div className="agent-answer" aria-live="polite">
          {result.mode !== "langchain_agent" && (
            <p className="privacy-line">
              智能核实未完整完成，以下采用有来源的资料建议。
            </p>
          )}
          <h3>{result.summary}</h3>
          {result.question_note && <p>{result.question_note}</p>}
          {!!result.report_facts?.length && (
            <div className="report-facts">
              {result.report_facts.map((f) => (
                <p key={f}>{f}</p>
              ))}
            </div>
          )}
          <ol>
            {result.actions.map((a) => (
              <li key={a}>{a}</li>
            ))}
          </ol>
          <h4>建议依据</h4>
          <div className="sources-grid">
            {result.sources.map((s) => (
              <a
                className="source-card"
                href={/^https:\/\//.test(s.url) ? s.url : undefined}
                key={s.id}
                target="_blank"
                rel="noopener noreferrer"
              >
                <strong>{s.title} ↗</strong>
                <p>{s.snippet}</p>
                <small>官方公开资料{s.date ? " · " + s.date : ""}</small>
              </a>
            ))}
          </div>
        </div>
      )}
      <div className="feedback-row">
        <span>这份结果对你有帮助吗？</span>
        {[
          ["useful", "有帮助"],
          ["not_useful", "没解决疑问"],
          ["false_alarm", "疑似误报"],
          ["missed_risk", "疑似漏报"],
        ].map(([v, t]) => (
          <button
            key={v}
            aria-pressed={feedback === v}
            onClick={() => void rate(v)}
          >
            {t}
          </button>
        ))}
        {feedbackNote && <p role="status">{feedbackNote}</p>}
      </div>
    </section>
  );
}
