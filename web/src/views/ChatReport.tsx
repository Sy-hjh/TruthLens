import { focusQuestions } from "../ui";
import { useState } from "react";
import { api, downloadReport } from "../api";
import type { Report } from "../api";
export function ChatTextReview({
  report,
  onUpdate,
}: {
  report: Report;
  onUpdate: (r: Report) => void;
}) {
  const [editing, setEditing] = useState(false),
    [text, setText] = useState(report.ocr?.text || ""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function save() {
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("text", text);
      onUpdate(
        await api(
          "/api/cases/" + report.id + "/chat-text",
          { method: "POST", body: form },
          120000,
        ),
      );
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "没有保存成功");
    } finally {
      setBusy(false);
    }
  }
  return <>
    <details open={editing}>
      <summary>核对截图文字</summary>
      {editing ? <>
        <label className="field">按截图修改
          <textarea rows={8} maxLength={4000} value={text} onChange={(e) => setText(e.target.value)} />
        </label>
        <button className="primary" disabled={busy || !text.trim()} onClick={save}>
          {busy ? "正在重查…" : "确认并重查"}
        </button>
      </> : <p className="transcript" style={{ whiteSpace: "pre-wrap" }}>{report.ocr?.text}</p>}
    </details>
    {!editing && <button onClick={() => setEditing(true)}>修改文字并重查</button>}
    {error && <p role="alert" className="error">{error}</p>}
  </>;
}

export default function ChatReport({report, onUpdate}: {report: Report; onUpdate: (r: Report) => void}) {
  const signals = report.chat_analysis?.signals || [],
    assessment = report.chat_analysis?.assessment;
  return (
    <>
      <div className="report-top">
        <div>
          <p className="eyebrow">发现了什么 · 聊天内容</p>
          <h1>{report.summary}</h1>
          <p>{report.filename}</p>
        </div>
        <div className="toolbar">
          <a className="report-pdf-export" href={`/api/cases/${encodeURIComponent(report.id)}/pdf`} download>导出 PDF</a>
          <button onClick={focusQuestions}>问问真鉴 ↓</button>
          <button onClick={() => downloadReport(report)}>下载记录</button>
          <button onClick={() => window.print()}>打印</button>
        </div>
      </div>
      <article
        className={
          "result-banner " +
          (assessment?.level === "alert" ? "alert" : "uncertain")
        }
      >
        <div>
          <span className="result-icon" aria-hidden="true">
            {assessment?.level === "alert" ? "!" : "?"}
          </span>
          <div>
            <h2>
              {assessment?.title ||
                (signals.length ? "这些要求需要警惕" : "先核实来源")}
            </h2>
            <p>
              {assessment?.summary ||
                (signals.length
                  ? "已提取到风险要求。此旧报告请修改文字并重查，查看新版套路说明和案例。"
                  : "原话和相关记录可帮助核实消息来源与要求。")}
            </p>
          </div>
        </div>
      </article>
      <section className="report-evidence" aria-labelledby="chat-evidence-title">
        <h2 id="chat-evidence-title">依据是什么</h2>
        {assessment?.cases?.length ? (
          <article className="card">
            <h2>相关公开案例</h2>
            {assessment.cases.map((c) => (
              <section key={c.url}>
                <h3>{c.title}</h3>
                <p>{c.summary}</p>
                <p>{c.connection}</p>
                <a href={c.url} target="_blank" rel="noreferrer">
                  查看警方原文 ↗
                </a>
                <small>
                  {c.publisher} · {c.date}发布；这是历史案例，不冒充今日新闻。
                </small>
              </section>
            ))}
          </article>
        ) : null}
        <article className="card">
          <h3>本次提示依据</h3>
          <p>
            {assessment?.summary ||
              (signals.length
                ? "原话中已发现需要核实的要求，不能因实验分类器没分出套路而忽略。"
                : "本次没有提取到明确风险要求；这不证明身份真实。")}
          </p>
          <p className="muted">
            判断依据是下面的原话与要求组合，相似案例不是对这次聊天的定罪。
          </p>
        </article>
        <article className="card">
          <h2>原话中需要核实的地方</h2>
          <p>{report.chat_analysis?.summary}</p>
          {signals.length ? (
            signals.map((s, i) => (
              <div className="phrase" key={i}>
                <h3>{s.title}</h3>
                <blockquote>{s.quote}</blockquote>
                {s.context && (
                  <details>
                    <summary>看上下文</summary>
                    <p style={{ whiteSpace: "pre-wrap" }}>{s.context}</p>
                  </details>
                )}
              </div>
            ))
          ) : (
            <p>
              {report.chat_analysis?.extraction_status === "unavailable"
                ? "原话分析暂不可用，请自己核对截图。"
                : "没有提取出明确要求，不代表聊天安全。"}
            </p>
          )}
        </article>
        <article className="card">
          {report.ocr?.text && <ChatTextReview report={report} onUpdate={onUpdate} />}
          <p className="muted">这里检查聊天套路，不鉴定文字是不是 AI 写的。</p>
        </article>
      </section>
      <article className="card final-steps">
        <h2>下一步怎么核实</h2>
        <p>{report.fraud_risk?.next_step || "对照原会话核对原话，再从原订单或原业务系统确认消息来源。"}</p>
        <button className="primary" onClick={focusQuestions}>结合报告提问 ↓</button>
      </article>
    </>
  );
}
