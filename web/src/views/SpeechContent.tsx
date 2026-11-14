import { useState } from "react";
import { api } from "../api";
import type { Report } from "../api";
export default function SpeechContent({
  report,
  onUpdate,
}: {
  report: Report;
  onUpdate: (r: Report) => void;
}) {
  const [editing, setEditing] = useState(false),
    [text, setText] = useState(report.transcript?.text || ""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const content = report.speech_analysis,
    a = content?.assessment;
  async function save() {
    setBusy(true);
    setError("");
    try {
      const data = new FormData();
      data.append("text", text);
      onUpdate(
        await api<Report>(
          "/api/cases/" + report.id + "/speech-text",
          { method: "POST", body: data },
          180000,
        ),
      );
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "重查失败");
    } finally {
      setBusy(false);
    }
  }
  return (
    <article
      className={
        "card " +
        (a?.level === "alert"
          ? "speech-content-alert"
          : a?.level === "attention"
            ? "analysis-incomplete"
            : "")
      }
    >
      <h2>说话内容风险检查</h2>
      <h3>
        {a?.title ||
          (content ? "本次内容分析未完成" : "此旧报告没有内容检查，请重新上传")}
      </h3>
      <p>{a?.summary || content?.note}</p>
      <p>
        转写可能听错，请先核对。内容提醒不表示声音是AI，也不能确认说话人身份。转写文字随报告保存，可在核验记录中删除。
      </p>
      {content?.signals?.map((s, i) => (
        <div className="phrase" key={i}>
          <strong>{s.title}</strong>
          <blockquote>{s.quote}</blockquote>
        </div>
      ))}
      {a?.cases?.map((c) => (
        <section key={c.url}>
          <h3>相似真实案例：{c.title}</h3>
          <p>{c.summary}</p>
          <p>{c.connection}</p>
          <a href={c.url} target="_blank" rel="noreferrer">
            查看警方原文 ↗
          </a>
          <small>
            {c.publisher} · {c.date}
          </small>
        </section>
      ))}
      <details open={editing}>
        <summary>核对声音转成的文字</summary>
        {editing ? (
          <>
            <textarea
              aria-label="校正转写文字"
              rows={6}
              maxLength={4000}
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <button disabled={busy || !text.trim()} onClick={save}>
              {busy ? "正在重查内容…" : "确认并重查内容"}
            </button>
            <button disabled={busy} onClick={() => setEditing(false)}>
              取消编辑
            </button>
          </>
        ) : (
          <p style={{ whiteSpace: "pre-wrap" }}>
            {report.transcript?.text ||
              report.transcript?.note ||
              "没有转写记录"}
          </p>
        )}
      </details>
      {report.transcript?.text && !editing && (
        <button
          onClick={() => {
            setText(report.transcript?.text || "");
            setEditing(true);
          }}
        >
          文字听错了？修改并重查
        </button>
      )}
      {report.transcript?.corrected && (
        <p>本项按您校正的文字分析；画面、声学分数没有因此改变。</p>
      )}
      {error && <p role="alert">{error}</p>}
    </article>
  );
}
