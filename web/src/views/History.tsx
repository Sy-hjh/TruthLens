import { Dialog } from "../ui";
import { useEffect, useState } from "react";
import { api } from "../api";
import type { Report } from "../api";
export default function History({ onOpen }: { onOpen: (r: Report) => void }) {
  const [pending, setPending] = useState<Report | null>(null);
  const [rows, setRows] = useState<Report[]>([]),
    [error, setError] = useState(""),
    [query, setQuery] = useState(""),
    [loading, setLoading] = useState(true);
  async function refresh() {
    setLoading(true);
    setError("");
    try {
      setRows(
        (await api<Report[]>("/api/cases")).filter(
          (r) =>
            !r.context?.startsWith("公开研究数据对照") &&
            !r.context?.startsWith("明确标注的通用合成语音反诈模拟"),
        ),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "读取失败");
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void refresh();
    const ready = () => void refresh();
    addEventListener("truthlens:report-ready", ready);
    return () => removeEventListener("truthlens:report-ready", ready);
  }, []);
  async function remove(id: string) {
    try {
      await api("/api/cases/" + id, { method: "DELETE" });
      setRows((x) => x.filter((r) => r.id !== id));
      setPending(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  }
  return (
    <>
      <p className="eyebrow">材料已删除 · 结果可回看</p>
      <h1>我的核验记录</h1>
      <p className="page-intro">
        核验结果和图片标记可在这里回看。上传文件处理后删除。
      </p>
      <label className="search field">
        查找材料
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入文件名或核验摘要"
        />
      </label>
      {error && (
        <p className="error" role="alert">
          {error}{" "}
          <button className="quiet" onClick={() => void refresh()}>
            重新读取
          </button>
        </p>
      )}
      {loading ? (
        <p role="status">正在读取记录…</p>
      ) : rows.filter((r) => (r.filename + r.summary).includes(query))
          .length ? (
        rows
          .filter((r) => (r.filename + r.summary).includes(query))
          .map((r) => (
            <article className="card history-row" key={r.id}>
              <span className="file-badge">▤</span>
              <div>
                <h2>{r.filename}</h2>
                <p>{r.summary}</p>
                <small>{new Date(r.created_at).toLocaleString("zh-CN")}</small>
              </div>
              <button
                className="primary"
                onClick={async () => {
                  try {
                    onOpen(await api("/api/cases/" + r.id));
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "报告读取失败");
                  }
                }}
              >
                查看报告 →
              </button>
              <button className="quiet" onClick={() => setPending(r)}>
                删除
              </button>
            </article>
          ))
      ) : (
        <article className="empty card">
          <h2>{query ? "没有找到匹配记录" : "还没有核验记录"}</h2>
          <p>检查材料后，报告会保存在这里。</p>
        </article>
      )}
      {pending && (
        <Dialog title="删除这条核验记录？" onClose={() => setPending(null)}>
          <p>{pending.filename}</p>
          <p>报告、标记缩略图、转写与对应反馈会一并清除。</p>
          <div className="toolbar">
            <button onClick={() => setPending(null)}>保留记录</button>
            <button className="primary" onClick={() => void remove(pending.id)}>
              确认删除
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
