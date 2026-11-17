import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Report } from "./api";
import { errorText } from "./ui";

export type CompanionJob = { id: string; filename: string };
type JobStatus = { status: string; message: string; result?: Report };
type ReportAdvice = { answer: string; actions?: string[] };

const jobKey = "truthlens-companion-verification";
const adviceKey = "truthlens-companion-advice-report";
let currentAdvice: { reportId: string; request: Promise<ReportAdvice> } | null = null;

export function savedCompanionJob(): CompanionJob | null {
  try {
    const job = JSON.parse(sessionStorage.getItem(jobKey) || "null");
    return job && typeof job.id === "string" && /^[a-z\d-]+$/i.test(job.id) &&
      typeof job.filename === "string" ? job : null;
  } catch {
    return null;
  }
}

export function storeCompanionJob(job: CompanionJob | null) {
  try {
    if (job) sessionStorage.setItem(jobKey, JSON.stringify(job));
    else sessionStorage.removeItem(jobKey);
  } catch {}
}

export function savedCompanionAdvice(): string {
  try {
    return sessionStorage.getItem(adviceKey) || "";
  } catch {
    return "";
  }
}

export function storeCompanionAdvice(reportId: string) {
  try {
    sessionStorage.setItem(adviceKey, reportId);
  } catch {}
}

function loadReportAdvice(reportId: string): Promise<ReportAdvice> {
  if (currentAdvice?.reportId === reportId) return currentAdvice.request;
  const request = api<ReportAdvice>("/api/companion/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      page: "report",
      question: "结合这次报告和事情经过，我下一步该怎么核实？",
      report_id: reportId,
    }),
    signal: AbortSignal.timeout(100000),
  }).catch((e) => {
    if (currentAdvice?.request === request) currentAdvice = null;
    throw e;
  });
  currentAdvice = { reportId, request };
  return request;
}

export function CompanionProgress({ job, onComplete, onDismiss }: {
  job: CompanionJob;
  onComplete: (report: Report) => void;
  onDismiss: () => void;
}) {
  const [message, setMessage] = useState("材料已提交，正在等待核验…");
  const [error, setError] = useState("");
  const [terminal, setTerminal] = useState(false);
  const [retry, setRetry] = useState(0);
  const complete = useRef(onComplete);
  complete.current = onComplete;

  useEffect(() => {
    const controller = new AbortController();
    let nextCheck: number | undefined;
    async function check() {
      try {
        const current = await api<JobStatus>("/api/jobs/" + job.id, {
          signal: AbortSignal.any([controller.signal, AbortSignal.timeout(15000)]),
        });
        if (controller.signal.aborted) return;
        if (current.status === "completed" && current.result) {
          complete.current(current.result);
        } else if (current.status === "failed") {
          setTerminal(true);
          setError(current.message);
        } else if (current.status === "processing") {
          setMessage(current.message);
          nextCheck = window.setTimeout(() => void check(), 1200);
        } else {
          setError("未收到完整的核验进度，可以重试。");
        }
      } catch (e) {
        if (!controller.signal.aborted) setError(errorText(e));
      }
    }
    void check();
    return () => {
      controller.abort();
      window.clearTimeout(nextCheck);
    };
  }, [job.id, retry]);

  return (
    <article className="card upload-card">
      <div className="card-heading"><div><h1>核验小鉴收到的材料</h1><p>{job.filename}</p></div></div>
      {error ? (
        <>
          <p className="error" role="alert">{error}</p>
          <div className="companion-tools">
            {!terminal && <button type="button" onClick={() => {
              setError("");
              setRetry((value) => value + 1);
            }}>重试查看进度</button>}
            <button type="button" onClick={onDismiss}>返回核验工作台</button>
          </div>
        </>
      ) : (
        <div className="progress"><div role="status"><span className="spinner" />{message}</div></div>
      )}
    </article>
  );
}

export function CompanionReportAdvice({ reportId }: { reportId: string }) {
  const [result, setResult] = useState<ReportAdvice | null>(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    void loadReportAdvice(reportId).then((advice) => {
      if (active) setResult(advice);
    }).catch((e) => {
      if (active) setError(errorText(e));
    });
    return () => { active = false; };
  }, [reportId, retry]);

  return (
    <article className="card companion-answer" aria-label="小鉴核实建议">
      <h2>小鉴的核实建议</h2>
      {result && <p>{[result.answer, ...(result.actions || [])].join(" ")}</p>}
      {!result && !error && <p role="status">正在结合报告和事情经过生成建议…</p>}
      {error && (
        <>
          <p className="error" role="alert">{error}</p>
          <button type="button" onClick={() => {
            setError("");
            setRetry((value) => value + 1);
          }}>重试生成建议</button>
        </>
      )}
    </article>
  );
}
