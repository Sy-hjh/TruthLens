import { Dialog } from "../ui";
import { useEffect, useState } from "react";
import { api } from "../api";
import { cases } from "../quiz-data";
interface News {
  id: string;
  title: string;
  url: string;
  published_at: string;
  source: string;
  topic: string;
  tip: string;
}
interface Feed {
  items: News[];
  checked_at: string | null;
  last_error: string | null;
  updating: boolean;
}
function readProgress() {
  try {
    const v = JSON.parse(sessionStorage.getItem("truthlens-quiz") || "null");
    if (
      v &&
      Number.isInteger(v.index) &&
      v.index >= 0 &&
      v.index < cases.length &&
      (v.choice === null ||
        (Number.isInteger(v.choice) &&
          v.choice >= 0 &&
          v.choice < cases[v.index].answers.length)) &&
      Number.isInteger(v.right) &&
      v.right >= 0 &&
      v.right <= cases.length &&
      Array.isArray(v.mistakes) &&
      v.mistakes.every((s: unknown) => typeof s === "string") &&
      typeof v.finished === "boolean"
    )
      return v as {
        index: number;
        choice: number | null;
        right: number;
        mistakes: string[];
        finished: boolean;
      };
    return null;
  } catch {
    return null;
  }
}
export default function Practice() {
  const saved = readProgress();
  const [confirmReset, setConfirmReset] = useState(false);
  const [index, setIndex] = useState(
      saved && saved.index >= 0 && saved.index < cases.length ? saved.index : 0,
    ),
    [choice, setChoice] = useState<number | null>(saved?.choice ?? null),
    [mode, setMode] = useState<"quiz" | "news">("quiz"),
    [right, setRight] = useState(saved?.right ?? 0),
    [mistakes, setMistakes] = useState<string[]>(saved?.mistakes ?? []),
    [finished, setFinished] = useState(saved?.finished ?? false),
    [feed, setFeed] = useState<Feed | null>(null),
    [newsError, setNewsError] = useState("");
  useEffect(() => {
    try {
      sessionStorage.setItem(
        "truthlens-quiz",
        JSON.stringify({ index, choice, right, mistakes, finished }),
      );
    } catch {}
  }, [index, choice, right, mistakes, finished]);
  async function load(refresh = false) {
    try {
      setFeed(await api("/api/news" + (refresh ? "?refresh=true" : "")));
      setNewsError("");
    } catch (e) {
      setNewsError(e instanceof Error ? e.message : "暂时没能读取预警");
    }
  }
  useEffect(() => {
    void load();
  }, []);
  useEffect(() => {
    if (!feed?.updating) return;
    const timer = setTimeout(() => void load(), 2500);
    return () => clearTimeout(timer);
  }, [feed]);
  const item = cases[index];
  function answer(i: number) {
    if (choice !== null) return;
    setChoice(i);
    if (i === item.correct) setRight((v) => v + 1);
    else setMistakes((v) => [...v, item.id]);
  }
  function next() {
    if (index === cases.length - 1) setFinished(true);
    else {
      setIndex(index + 1);
      setChoice(null);
    }
  }
  function reset() {
    setIndex(0);
    setChoice(null);
    setRight(0);
    setMistakes([]);
    setFinished(false);
  }
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (
        mode !== "quiz" ||
        finished ||
        confirmReset ||
        document.querySelector("dialog[open]") ||
        (e.target as HTMLElement)?.closest(
          "input,textarea,select,button,[contenteditable=true]",
        )
      )
        return;
      const n = ["1", "2", "3"].indexOf(e.key);
      if (n >= 0 && choice === null) {
        e.preventDefault();
        answer(n);
      }
    };
    addEventListener("keydown", key);
    return () => removeEventListener("keydown", key);
  }, [mode, index, choice, finished, confirmReset]);
  return (
    <>
      <p className="eyebrow">把核实方法，慢慢练熟</p>
      <h1>练习识别骗局</h1>
      <p className="page-intro">先看情景怎么应对，也看看最近有哪些新套路。</p>
      <div className="practice-tabs">
        <button
          className={mode === "quiz" ? "active" : ""}
          onClick={() => setMode("quiz")}
        >
          情景练习 · {cases.length}题
        </button>
        <button
          className={mode === "news" ? "active" : ""}
          onClick={() => setMode("news")}
        >
          最近的诈骗预警
        </button>
      </div>
      {mode === "quiz" && (
        <div className="practice-tools">
          <progress
            aria-label="本轮答题进度"
            value={index + (choice !== null ? 1 : 0)}
            max={cases.length}
          />
          <button className="text-button" onClick={() => setConfirmReset(true)}>
            重开本轮
          </button>
        </div>
      )}
      {mode === "quiz" ? (
        finished ? (
          <article className="card quiz">
            <h2>这一轮练完了</h2>
            <p className="practice-summary">
              答对 {right} / {cases.length} 题
            </p>
            <p>
              {mistakes.length
                ? `有${mistakes.length}道题值得再看看。遇到陌生要求，记住先停、再核实。`
                : "您已经把这轮核实方法练了一遍。"}
            </p>
            {mistakes.length > 0 && (
              <div>
                {cases
                  .filter((q) => mistakes.includes(q.id))
                  .map((q) => (
                    <p key={q.id}>
                      <b>{q.title}</b>：{q.why}
                    </p>
                  ))}
              </div>
            )}
            <button className="primary" onClick={reset}>
              再练一轮
            </button>
            <button onClick={() => setMode("news")}>看看最新预警</button>
          </article>
        ) : (
          <article className="card quiz">
            <div className="quiz-progress">
              <span>
                第 {index + 1} / {cases.length} 题
              </span>
              <span>已答对 {right} 题</span>
            </div>
            <h2>{item.title}</h2>
            <p className="scenario">{item.text}</p>
            <div className="answers">
              {item.answers.map((text, i) => {
                const correct = choice !== null && i === item.correct;
                const wrong = choice === i && i !== item.correct;
                return (
                  <button
                    key={i}
                    className={
                      correct ? "answer-correct" : wrong ? "answer-wrong" : ""
                    }
                    disabled={choice !== null}
                    onClick={() => answer(i)}
                  >
                    <span>{String.fromCharCode(65 + i)}</span>
                    {text}
                    {correct && <b className="answer-state">✓ 正确选项</b>}
                    {wrong && <b className="answer-state">✕ 您选错了</b>}
                  </button>
                );
              })}
            </div>
            {choice !== null && (
              <div
                className={
                  "quiz-feedback " +
                  (choice === item.correct ? "correct" : "wrong")
                }
                role="status"
              >
                <h3>
                  {choice === item.correct
                    ? "答对了，这样更稳妥"
                    : "这次选错了，请看绿色的正确选项"}
                </h3>
                <p>{item.why}</p>
                <button className="primary" onClick={next}>
                  {index === cases.length - 1 ? "查看本轮结果" : "下一题 →"}
                </button>
              </div>
            )}
            <p className="quiz-source">
              这些是为学习核实方法编写的情景，不冒充真实案件报道。
            </p>
          </article>
        )
      ) : (
        <>
          <div className="news-status">
            <b>{feed?.updating ? "正在核对来源更新…" : "公开预警"} </b>
            {feed?.checked_at
              ? `最近检查：${new Date(feed.checked_at).toLocaleString("zh-CN")}`
              : "首次联网后更新；以下有明确来源和发布日期。"}
            <button onClick={() => load(true)}>检查更新</button>
            <small>
              网站运行时每6小时检查一次。发布日期以来源为准，并非每天都有新案发布。
            </small>
            {(newsError || feed?.last_error) && (
              <p>{newsError || feed?.last_error}</p>
            )}
          </div>
          <div className="news-grid">
            {feed?.items.map((n) => (
              <article className="card news-card" key={n.id}>
                <div className="news-meta">
                  {n.source} · {n.published_at}
                </div>
                <h2>{n.title}</h2>
                <div className="news-tip">
                  <b>记住这一点</b>
                  <p>{n.tip}</p>
                </div>
                <a href={n.url} target="_blank" rel="noreferrer">
                  查看来源原文 ↗
                </a>
              </article>
            ))}
          </div>
          {!feed && !newsError && <p role="status">正在读取带来源的预警…</p>}
        </>
      )}
      <section className="card practice-faq">
        <p className="eyebrow">GOOD TO KNOW</p>
        <h2>你可能还想知道</h2>
        {[
          [
            "检测没发现合成，就能相信吗？",
            "不能。检测可能漏检，熟悉的账号也可能被冒用。涉及钱和身份，仍需通过原先保存的号码确认。",
          ],
          [
            "AI合成内容一定是骗局吗？",
            "不是。合成是材料的制作方式，骗局还涉及来源、身份与具体要求，两者需要分别核实。",
          ],
          [
            "为什么不要直接拨打消息里发来的号码？",
            "这个号码也可能由对方控制。请使用事先保存并核对过的号码，或与可信的家人当面确认。",
          ],
        ].map(([q, a]) => (
          <details key={q}>
            <summary>{q}</summary>
            <p>{a}</p>
          </details>
        ))}
      </section>
      {confirmReset && (
        <Dialog title="重新开始这一轮？" onClose={() => setConfirmReset(false)}>
          <p>本轮作答进度将重置，你可以从第一题重新练习。</p>
          <div className="toolbar">
            <button onClick={() => setConfirmReset(false)}>继续当前练习</button>
            <button
              className="primary"
              onClick={() => {
                reset();
                setConfirmReset(false);
              }}
            >
              确认重开
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
