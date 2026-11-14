import { useEffect, useId, useRef, useState } from "react";
import { streamAdvice } from "./api";
import type { Report } from "./api";
import { Dialog, Icon, errorText } from "./ui";
interface Answer {
  answer: string;
  actions?: string[];
  mode: string;
  note: string;
  guides: { id: string; title: string; page: string }[];
  sources: { id: string; title: string; url: string }[];
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
}: {
  motion: boolean;
  page: string;
  report: Report | null;
  onNavigate: (page: string) => void;
}) {
  const [open, setOpen] = useState(false),
    [question, setQuestion] = useState(""),
    [busy, setBusy] = useState(false),
    [answer, setAnswer] = useState<Answer | null>(null),
    [error, setError] = useState(""),
    [roam, setRoam] = useState(true),
    [position, setPosition] = useState<{ x: number; y: number } | null>(null),
    [useReport, setUseReport] = useState(false);
  const abort = useRef<AbortController | null>(null),
    drag = useRef<{
      x: number;
      y: number;
      left: number;
      top: number;
      moved: boolean;
    } | null>(null),
    moved = useRef(false);
  useEffect(() => {
    const show = () => setOpen(true);
    addEventListener("truthlens:companion", show);
    return () => {
      removeEventListener("truthlens:companion", show);
      abort.current?.abort();
    };
  }, []);
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
  async function ask(q: string) {
    if (busy || !q.trim()) return;
    setQuestion(q);
    setBusy(true);
    setError("");
    setAnswer(null);
    abort.current = new AbortController();
    const timer = setTimeout(() => abort.current?.abort(), 180000);
    try {
      if (useReport && report) {
        const r = await streamAdvice(
          report.id,
          q,
          () => {},
          abort.current.signal,
        );
        setAnswer({
          answer: [
            r.summary,
            r.question_note,
            ...(r.report_facts || []),
            ...r.actions,
          ]
            .filter(Boolean)
            .join("\n\n"),
          mode: r.mode,
          note: "结合当前报告与反诈资料；不确认身份。",
          guides: [],
          sources: r.sources,
        });
      } else {
        const response = await fetch("/api/companion/ask", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: q.trim(), page }),
          signal: abort.current.signal,
        });
        const data = await response.json();
        if (!response.ok)
          throw Error(data.detail || "助手暂时繁忙，请稍后重试");
        setAnswer(data as Answer);
      }
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
        <span className="companion-bubble">
          问问小鉴 <span>✦</span>
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
            if (!moved.current) setOpen(true);
          }}
        >
          <Robot mood={busy ? "thinking" : "idle"} />
        </button>
      </div>
      {open && (
        <Dialog title="小鉴 · 你的核实搭子" onClose={() => setOpen(false)}>
          <div className="companion-content">
            <div className="companion-intro">
              <Robot mood={busy ? "thinking" : "idle"} />
              <div>
                <span className="companion-status">
                  <i />
                  {busy ? "正在查阅与回答" : "在这里，陪你多核实一步"}
                </span>
                <p>问使用方法、检测结果或反诈核实。请不要输入密码、验证码。</p>
              </div>
            </div>
            <div className="companion-tools">
              <button
                aria-pressed={roam}
                onClick={() => {
                  setRoam(!roam);
                  setPosition(null);
                }}
              >
                {roam ? "暂停小鉴巡游" : "开启小鉴巡游"}
              </button>
              {page === "report" && report && (
                <button
                  aria-pressed={useReport}
                  onClick={() => setUseReport(!useReport)}
                >
                  {useReport ? "已结合当前报告" : "结合当前报告提问"}
                </button>
              )}
            </div>
            <div className="companion-prompts">
              {[
                "视频会检查哪些内容？",
                "检测没有异常，能转钱吗？",
                "你是专门微调过的吗？",
              ].map((q) => (
                <button disabled={busy} key={q} onClick={() => void ask(q)}>
                  {q}
                  <Icon name="arrow" />
                </button>
              ))}
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void ask(question);
              }}
              className="companion-form"
            >
              <textarea
                aria-label="向小鉴提问"
                placeholder="比如：声音特别像家人，我该怎么核实？"
                maxLength={320}
                rows={2}
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={busy}
              />
              <button className="primary" disabled={busy || !question.trim()}>
                发送问题 <Icon name="arrow" />
              </button>
            </form>
            {busy && (
              <div className="companion-thinking" role="status">
                <span />
                <span />
                <span /> 本地模型正在回答，首次加载可能较慢。
                <button onClick={() => abort.current?.abort()}>停止等待</button>
              </div>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            {answer && (
              <div className="companion-answer" aria-live="polite">
                <span className="eyebrow">小鉴的回答</span>
                <p>{answer.answer}</p>
                <small>{answer.note}</small>
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
          </div>
        </Dialog>
      )}
    </>
  );
}
