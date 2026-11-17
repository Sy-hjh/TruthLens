import { useEffect, useId, useRef, useState } from "react";
import type { Report } from "./api";
import { Dialog, Icon, errorText } from "./ui";
import CompanionMedia from "./CompanionMedia";
import type { MaterialKind } from "./CompanionMedia";
import type { CompanionJob } from "./CompanionVerification";
import { localFileReference } from "./companionDesktop";
interface Answer {
  answer: string;
  actions?: string[];
  material?: MaterialKind | "any" | null;
  material_options?: MaterialKind[];
  local_paths?: string[];
  mode: string;
  note: string;
  guides: { id: string; title: string; page: string }[];
  sources: { id: string; title: string; url: string }[];
}
interface CompanionModelStatus {
  mode: "local" | "online" | "configuration_error";
  message?: string;
}
export function Robot({ mood = "idle" }: { mood?: string }) {
  const uid = useId();
  return (
    <svg
      viewBox="0 0 140 160"
      className={"robot-svg robot-" + mood}
      aria-hidden="true"
    >
      <defs>
        <linearGradient id={uid + "shell"} x2=".8" y2="1">
          <stop stopColor="#faf5ff" />
          <stop offset="1" stopColor="#a99acb" />
        </linearGradient>
        <linearGradient id={uid + "visor"}>
          <stop stopColor="#24172f" />
          <stop offset="1" stopColor="#4b3563" />
        </linearGradient>
      </defs>
      <ellipse
        className="robot-shadow"
        cx="70"
        cy="146"
        rx="34"
        ry="6"
        fill="#21182525"
      />
      <g className="robot-body">
        <path d="M70 24V12" stroke="#bda7e8" strokeWidth="4" />
        <circle
          className="robot-antenna"
          cx="70"
          cy="10"
          r="6"
          fill="#dbff48"
        />
        <rect
          x="24"
          y="28"
          width="92"
          height="70"
          rx="27"
          fill={"url(#" + uid + "shell)"}
          stroke="#ffffff"
          strokeWidth="2"
        />
        <rect
          x="33"
          y="39"
          width="74"
          height="44"
          rx="19"
          fill={"url(#" + uid + "visor)"}
        />
        <g className="robot-eyes" fill="#dbff48">
          <rect x="46" y="51" width="10" height="18" rx="5" />
          <rect x="84" y="51" width="10" height="18" rx="5" />
        </g>
        <path
          d="M61 73q9 6 18 0"
          stroke="#dbff48"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M44 103Q70 94 96 103L101 128Q70 143 39 128Z"
          fill={"url(#" + uid + "shell)"}
          stroke="#fff"
        />
        <circle cx="70" cy="116" r="10" fill="#322141" />
        <path
          d="m66 116 3 3 6-7"
          stroke="#dbff48"
          fill="none"
          strokeWidth="3"
        />
        <path
          className="robot-arm left"
          d="M37 105 24 119"
          stroke="#c7b8dc"
          strokeWidth="9"
          strokeLinecap="round"
        />
        <path
          className="robot-arm right"
          d="m103 105 13-14"
          stroke="#c7b8dc"
          strokeWidth="9"
          strokeLinecap="round"
        />
        <path
          className="robot-leg left"
          d="m55 134-5 8"
          stroke="#bca6d3"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          className="robot-leg right"
          d="m85 134 5 8"
          stroke="#bca6d3"
          strokeWidth="10"
          strokeLinecap="round"
        />
      </g>
    </svg>
  );
}
export default function Companion({
  motion,
  page,
  report,
  onNavigate,
  onVerificationStart,
  verificationPending,
  authenticated,
  onAuthRequired,
}: {
  motion: boolean;
  page: string;
  report: Report | null;
  onNavigate: (page: string) => void;
  onVerificationStart: (job: CompanionJob) => void;
  verificationPending: boolean;
  authenticated: boolean;
  onAuthRequired: () => void;
}) {
  const [open, setOpen] = useState(false),
    [question, setQuestion] = useState(""),
    [busy, setBusy] = useState(false),
    [busyText, setBusyText] = useState("正在查阅与回答"),
    [answer, setAnswer] = useState<Answer | null>(null),
    [modelError, setModelError] = useState(""),
    [currentReport, setCurrentReport] = useState<Report | null>(null),
    [error, setError] = useState(""),
    [roam, setRoam] = useState(true),
    [position, setPosition] = useState<{ x: number; y: number } | null>(null);
  const abort = useRef<AbortController | null>(null),
    history = useRef<{ question: string; answer: string }[]>([]),
    localFile = useRef({ folder: "", filename: "", description: "" }),
    drag = useRef<{
      x: number;
      y: number;
      left: number;
      top: number;
      moved: boolean;
    } | null>(null),
    moved = useRef(false);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setModelError("");
    void fetch("/api/companion/model", { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw Error("问答状态暂时无法读取");
        return response.json() as Promise<CompanionModelStatus>;
      })
      .then((status) => {
        if (!controller.signal.aborted && status.mode === "configuration_error") {
          setModelError(status.message || "模型配置有误，请检查后重试。");
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setModelError("暂时无法确认问答服务状态，请稍后重试。");
      });
    return () => controller.abort();
  }, [open]);
  useEffect(() => {
    const show = () => {
      if (authenticated) setOpen(true);
      else onAuthRequired();
    };
    addEventListener("truthlens:companion", show);
    return () => removeEventListener("truthlens:companion", show);
  }, [authenticated, onAuthRequired]);
  useEffect(() => () => abort.current?.abort(), []);
  useEffect(() => {
    const clamp = () =>
      setPosition((p) =>
        p
          ? {
              x: Math.min(p.x, innerWidth - 100),
              y: Math.min(p.y, innerHeight - 130),
            }
          : null,
      );
    addEventListener("resize", clamp);
    return () => removeEventListener("resize", clamp);
  }, []);
  const reportChoice = page === "report" && report ? report : currentReport;
  const attachedReport = reportChoice?.id === currentReport?.id ? currentReport : null;
  const conversationContext = history.current.map((turn) => turn.question).join("\n");
  function startVerification(description: string, job: CompanionJob) {
    localFile.current = { folder: "", filename: "", description: "" };
    setQuestion((current) => current.trim() === description ? "" : current);
    setAnswer(null);
    setCurrentReport(null);
    setOpen(false);
    onVerificationStart(job);
  }
  function showLocalPrompt(text: string, localPaths?: string[]) {
    setAnswer({ answer: text, local_paths: localPaths, mode: "material_guidance", note: "", guides: [], sources: [] });
    setQuestion("");
  }
  async function selectLocalFile(path: string, context: string, signal: AbortSignal, location = "", folderFilename = ""): Promise<CompanionJob | null> {
    const file = location === "desktop" ? { desktop_filename: path }
      : location ? { drive: location[0], filename: path }
      : folderFilename ? { path, filename: folderFilename } : { path };
    const response = await fetch("/api/companion/local-file", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...file, context }),
      signal,
    });
    if (response.status === 401) dispatchEvent(new Event("truthlens:auth-required"));
    const data = await response.json();
    if (response.ok) {
      return { id: data.job_id as string, filename: data.filename || path.split(/[\\/]/).pop() || "本机文件" };
    }
    if (data.detail?.code === "filename_required") {
      localFile.current.folder = path;
      const filename = localFile.current.filename;
      if (filename) return selectLocalFile(path, context, signal, "", filename);
      showLocalPrompt(data.detail.message);
      return null;
    }
    if (["ambiguous_file", "incomplete_file_search"].includes(data.detail?.code)) {
      showLocalPrompt(data.detail.message, data.detail.paths);
      return null;
    }
    throw Error(typeof data.detail === "string" ? data.detail : "读取文件失败，请核对路径。");
  }
  async function ask(q: string, reportToExplain = attachedReport) {
    if (busy || !q.trim()) return;
    setQuestion(q);
    setBusy(true);
    setBusyText("正在查阅与回答");
    setError("");
    setAnswer(null);
    abort.current = new AbortController();
    const timer = setTimeout(() => abort.current?.abort(), 180000);
    try {
      const text = q.trim();
      const drive = text.search(/(?<![a-z0-9_-])[a-z]:(?:\\|\/(?!\/))/i);
      const requestContext = answer?.local_paths?.includes(text) ? "" : text;
      const context = [conversationContext, localFile.current.description, requestContext].filter(Boolean).join("\n").slice(-4000);
      const pending = /^(?:desktop|[A-Z]盘)$/.test(localFile.current.folder) ? localFile.current.folder : "";
      const fileSearch = drive === -1 && localFileReference(text, pending);
      if (fileSearch) {
        if (verificationPending) {
          showLocalPrompt("请先等当前材料核验完成。");
          return;
        }
        const filename = fileSearch.filename || localFile.current.filename;
        const where = fileSearch.location === "desktop" ? "桌面上" : `${fileSearch.location}里`;
        localFile.current = { folder: fileSearch.location, filename, description: localFile.current.description || text };
        if (!filename) {
          showLocalPrompt(`请告诉我${where}这份材料的文件名。`);
          return;
        }
        setBusyText(`正在${where}查找文件`);
        const job = await selectLocalFile(filename, context, abort.current.signal, fileSearch.location);
        if (job) startVerification(text, job);
        return;
      }
      const extension = "(?:jpg|jpeg|png|webp|mp4|mov|avi|webm|wav|mp3|m4a|flac|ogg)";
      const filename = text.replace(/^(?:文件名[是为：:]?|名字[是为：:]?|是)\s*/, "").replace(/^["“]|["”。！？]+$/g, "");
      const bareFilename = new RegExp(`^[^\\\\/:*?"<>|\\r\\n]+\\.${extension}$`, "i").test(filename);
      if (drive !== -1 || bareFilename) {
        if (verificationPending) {
          showLocalPrompt("请先等当前材料核验完成。");
          return;
        }
        let path: string;
        if (drive !== -1) {
          if (/别|不要|不用|不必/.test(text.slice(0, drive))) {
            showLocalPrompt("需要核验时，可以发送文件的完整路径。");
            return;
          }
          const candidate = text.slice(drive).replace(/["”。！？；，]+$/g, "").trim();
          if (/[a-z]:[\\/]/i.test(candidate.slice(2))) {
            showLocalPrompt("请先告诉我要核验哪一份文件。");
            return;
          }
          const match = new RegExp(`^([^"”\\r\\n]+\\.${extension})(?=$|[\\s"”。！？；，])`, "i").exec(candidate);
          path = match?.[1] || candidate;
        } else if (localFile.current.folder) {
          path = localFile.current.folder.replace(/[\\/]+$/, "") + "\\" + filename;
        } else {
          localFile.current.filename = filename;
          showLocalPrompt("这个文件在哪个文件夹？也可以发我它的完整路径。");
          return;
        }
        const job = await selectLocalFile(path, context, abort.current.signal);
        if (job) startVerification(text, job);
        return;
      }
      localFile.current = { folder: "", filename: "", description: "" };
      const response = await fetch("/api/companion/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q.trim(),
          page,
          history: history.current,
          report_id: reportToExplain?.id,
        }),
        signal: abort.current.signal,
      });
      if (response.status === 401) dispatchEvent(new Event("truthlens:auth-required"));
      const data = await response.json();
      if (!response.ok)
        throw Error(data.detail || "助手暂时繁忙，请稍后重试");
      setAnswer(data as Answer);
      if (data.mode === "online_model_rag" || data.mode === "local_qwen_rag") setModelError("");
      if (data.mode !== "scope_guidance") {
        history.current = [...history.current, {
          question: q.trim(),
          answer: data.answer,
        }].slice(-5);
      }
      setQuestion("");
    } catch (e) {
      setError(
        e instanceof DOMException && e.name === "AbortError"
          ? "已停止等待，可以重新提问。"
          : errorText(e),
      );
    } finally {
      clearTimeout(timer);
      setBusy(false);
    }
  }
  const notice = error || (answer?.mode === "guide_fallback" ? answer.note : "") || modelError;
  return (
    <>
      <div
        className={
          "companion-dock " +
          (motion && roam && !position && !open ? "is-roaming" : "")
        }
        style={
          position
            ? {
                left: position.x,
                top: position.y,
                right: "auto",
                bottom: "auto",
              }
            : undefined
        }
      >
        <span
          className="companion-bubble"
          style={
            position
              ? {
                  left: `min(0px, calc(100vw - ${position.x + 190}px))`,
                  ...(position.y < 58 ? { bottom: "auto", top: "100%" } : {}),
                }
              : undefined
          }
        >
          你好，我是 AI 内容核验智能体小鉴
          <br />
          想做什么？直接跟我说。
        </span>
        <button
          className="companion-pet"
          aria-label="打开小鉴智能助手，可拖动换位置"
          onPointerDown={(e) => {
            const b = e.currentTarget.parentElement!.getBoundingClientRect();
            drag.current = {
              x: e.clientX,
              y: e.clientY,
              left: b.left,
              top: b.top,
              moved: false,
            };
            moved.current = false;
            e.currentTarget.setPointerCapture(e.pointerId);
          }}
          onPointerMove={(e) => {
            const d = drag.current;
            if (!d) return;
            const dx = e.clientX - d.x,
              dy = e.clientY - d.y;
            if (Math.hypot(dx, dy) > 5) d.moved = true;
            if (d.moved) {
              moved.current = true;
              setPosition({
                x: Math.max(0, Math.min(innerWidth - 100, d.left + dx)),
                y: Math.max(80, Math.min(innerHeight - 130, d.top + dy)),
              });
            }
          }}
          onPointerUp={() => {
            drag.current = null;
          }}
          onPointerCancel={() => {
            drag.current = null;
          }}
          onClick={() => {
            if (!moved.current) {
              if (authenticated) setOpen(true);
              else onAuthRequired();
            }
          }}
        >
          <Robot mood={busy ? "thinking" : "idle"} />
        </button>
      </div>
      {open && (
        <Dialog
          title="小鉴 · 你的核实搭子"
          onClose={() => setOpen(false)}
          headerAction={
            <button
              type="button"
              className="companion-roam-toggle"
              aria-pressed={roam}
              onClick={() => {
                setRoam(!roam);
                setPosition(null);
              }}
            >
              {roam ? "暂停小鉴巡游" : "开启小鉴巡游"}
            </button>
          }
        >
          <div className="companion-content">
            <div className="companion-intro">
              <Robot mood={busy ? "thinking" : "idle"} />
              <div>
                <span className="companion-status">
                  <i />
                  {busy ? busyText : "我是 AI 内容核验智能体小鉴"}
                </span>
                <p>说说你想核实什么，或发来图片、语音、视频和聊天截图。我会解释发现的线索，并给出复核建议。</p>
              </div>
            </div>
            {reportChoice && (
              <div className="companion-tools">
                <button
                  aria-pressed={!!attachedReport}
                  onClick={() => setCurrentReport(attachedReport ? null : reportChoice)}
                >
                  {attachedReport ? "已结合报告 · 取消" : "结合当前报告提问"}
                </button>
              </div>
            )}
            <div className="companion-prompts">
              {[
                "学生交的作业图片像是 AI 生成的，怎么查？",
                "客户提交的售后照片疑似改过，先核对什么？",
              ].map((q) => (
                <button disabled={busy} key={q} onClick={() => void ask(q)}>
                  {q}
                  <Icon name="arrow" />
                </button>
              ))}
            </div>
            {answer && (
              <div className="companion-answer" aria-live="polite">
                <span className="eyebrow">小鉴的回答</span>
                <p>{answer.answer}</p>
                {answer.local_paths?.length ? (
                  <div className="companion-prompts companion-local-files">
                    {answer.local_paths.map((path) => (
                      <button key={path} disabled={busy || verificationPending} onClick={() => void ask(path)}>
                        <span>{path}</span>
                        <Icon name="arrow" />
                      </button>
                    ))}
                  </div>
                ) : null}
                {!!answer.actions?.length && (
                  <div className="companion-safe">
                    <b>先这样做</b>
                    {answer.actions.map((a) => (
                      <p key={a}>{a}</p>
                    ))}
                  </div>
                )}
                {answer.guides.length > 0 && (
                  <div className="companion-shortcuts">
                    {answer.guides.map((g) => (
                      <button
                        key={g.id}
                        onClick={() => {
                          onNavigate(g.page);
                          setOpen(false);
                        }}
                      >
                        {g.title}
                        <Icon name="up" />
                      </button>
                    ))}
                  </div>
                )}
                {answer.sources.length > 0 && (
                  <details>
                    <summary>相关公开资料</summary>
                    {answer.sources.map((s) => (
                      <a
                        key={s.id}
                        href={s.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {s.title} ↗
                      </a>
                    ))}
                  </details>
                )}
              </div>
            )}
            <CompanionMedia
              disabled={busy || verificationPending}
              materialKind={answer?.material ?? null}
              materialOptions={answer?.material_options ?? []}
              question={question}
              conversationContext={conversationContext}
              onAttachmentSent={startVerification}
              onTranscript={(text) => setQuestion((draft) => [draft.trim(), text].filter(Boolean).join(" ").slice(0, 320))}
              renderComposer={(controls, attachment, onPaste) => (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    if (attachment) {
                      if (!attachment.disabled) attachment.send();
                    } else {
                      void ask(question);
                    }
                  }}
                  onPaste={onPaste}
                  className="companion-form"
                >
                  <div className="companion-input">
                    <textarea
                      aria-label="向小鉴提问"
                      placeholder="比如：这张图片的出处应该怎么核实？"
                      maxLength={320}
                      rows={2}
                      value={question}
                      onChange={(e) => setQuestion(e.target.value)}
                      disabled={busy}
                    />
                    {controls}
                  </div>
                  <button className="primary" disabled={busy || (attachment ? attachment.disabled : !question.trim())}>
                    {attachment ? "发送核验" : "发送问题"} <Icon name="arrow" />
                  </button>
                </form>
              )}
            />
            {busy && (
              <div className="companion-thinking" role="status">
                <span />
                <span />
                <span /> 小鉴正在理解你的问题…
                <button onClick={() => abort.current?.abort()}>停止等待</button>
              </div>
            )}
            {notice && (
              <p className="companion-notice" role="alert">
                {notice}
              </p>
            )}
          </div>
        </Dialog>
      )}
    </>
  );
}
