import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { Report } from "../api";
import { Icon, errorText } from "../ui";
type Kind = "general" | "chat";
type Job = { status: string; message: string; result?: Report };
const supported =
  /\.(mp4|mov|avi|webm|wav|mp3|m4a|flac|ogg|jpg|jpeg|png|webp)$/i;
export default function Upload({
  onComplete,
  onContacts,
}: {
  onComplete: (r: Report, all?: Report[]) => void;
  onContacts: () => void;
}) {
  const [scene, setScene] = useState<Kind>("general"),
    [files, setFiles] = useState<File[]>([]),
    [selected, setSelected] = useState(0),
    [preview, setPreview] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [error, setError] = useState(""),
    [drag, setDrag] = useState(false),
    [elapsed, setElapsed] = useState(0),
    [batchIndex, setBatchIndex] = useState(0),
    [stop, setStop] = useState(false);
  const mounted = useRef(true),
    stopRef = useRef(false),
    picker = useRef<HTMLInputElement>(null),
    started = useRef(0);
  const file = files[selected];
  const kind = file
    ? /\.(mp4|mov|avi|webm)$/i.test(file.name)
      ? "video"
      : /\.(mp3|m4a|wav|flac|ogg)$/i.test(file.name)
        ? "audio"
        : "image"
    : "";
  useEffect(() => {
    mounted.current = true;
    let pending = "";
    try {
      pending = sessionStorage.getItem("qinan-active-job") || "";
    } catch {}
    if (pending) {
      setBusy(true);
      started.current = Date.now();
      setMessage("正在恢复上次核验…");
      void watch(pending)
        .then((r) => {
          if (r && mounted.current) onComplete(r);
        })
        .catch((e) => {
          if (mounted.current) setError(errorText(e));
        })
        .finally(() => {
          if (mounted.current) setBusy(false);
        });
    }
    return () => {
      mounted.current = false;
    };
  }, []);
  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  useEffect(() => {
    if (!busy) return;
    const t = setInterval(
      () => setElapsed(Math.floor((Date.now() - started.current) / 1000)),
      1000,
    );
    return () => clearInterval(t);
  }, [busy]);
  function choose(list: FileList | null) {
    if (!list || busy) return;
    const next: File[] = [];
    const rejected: string[] = [];
    for (const f of Array.from(list)) {
      if (
        !supported.test(f.name) ||
        (scene === "chat" && !/\.(jpg|jpeg|png|webp)$/i.test(f.name))
      )
        rejected.push("不支持的格式：" + f.name);
      else if (f.size > 104857600) rejected.push("超过100MB：" + f.name);
      else if (f.size === 0) rejected.push("文件是空的：" + f.name);
      else next.push(f);
    }
    setFiles((old) => [...old, ...next].slice(0, 4));
    setError(
      rejected.length
        ? rejected.join("；")
        : files.length + next.length > 4
          ? "每次最多核验4份材料，多出的文件未添加。"
          : "",
    );
    if (picker.current) picker.current.value = "";
  }
  async function watch(id: string): Promise<Report | undefined> {
    let misses = 0;
    for (let i = 0; i < 1000; i++) {
      if (!mounted.current) return;
      let j: Job | undefined;
      try {
        j = await api<Job>("/api/jobs/" + id);
        misses = 0;
      } catch (e) {
        if (++misses >= 3) throw e;
      }
      if (j) {
        setMessage(j.message);
        if (j.status === "completed" && j.result) {
          try {
            sessionStorage.removeItem("qinan-active-job");
          } catch {}
          return j.result;
        }
        if (j.status === "failed") {
          try {
            sessionStorage.removeItem("qinan-active-job");
          } catch {}
          throw Error(j.message);
        }
      }
      await new Promise((r) => setTimeout(r, 1200));
    }
    throw Error("本次等待较久，可稍后到核验记录查看。");
  }
  async function submit() {
    if (!files.length || busy) return;
    setBusy(true);
    setError("");
    setElapsed(0);
    started.current = Date.now();
    stopRef.current = false;
    setStop(false);
    const completed: Report[] = [];
    try {
      for (let i = 0; i < files.length; i++) {
        if (stopRef.current) break;
        if (!mounted.current) return;
        setSelected(i);
        setBatchIndex(i);
        setMessage("正在提交材料…");
        const form = new FormData();
        form.append("file", files[i]);
        form.append("scene", scene);
        const { job_id } = await api<{ job_id: string }>(
          "/api/analyze",
          { method: "POST", body: form },
          60000,
        );
        try {
          sessionStorage.setItem("qinan-active-job", job_id);
        } catch {}
        const result = await watch(job_id);
        if (result) completed.push(result);
      }
      if (mounted.current && completed.length) {
        setFiles([]);
        setSelected(0);
        onComplete(completed[0], completed);
      }
    } catch (e) {
      if (mounted.current)
        setError(
          errorText(e) +
            (completed.length ? " 已完成的材料可以在核验记录查看。" : ""),
        );
    } finally {
      if (mounted.current) setBusy(false);
    }
  }
  const stage = /提交|准备|恢复/.test(message)
    ? 0
    : /读取|画面|图片|视频|声音|音轨/.test(message)
      ? 1
      : /转写|内容|文字/.test(message)
        ? 2
        : 1;
  return (
    <>
      <p className="eyebrow">01 / VERIFICATION WORKSPACE</p>
      <h1>把疑问，交给一次核验。</h1>
      <p className="page-intro">
        上传亲友发来的材料，分别查看合成线索与可疑要求。
      </p>
      <div className="check-grid">
        <article className="card upload-card">
          <div className="card-heading">
            <span className="step">01</span>
            <div>
              <h2>选择收到的材料</h2>
              <p>视频会分别检查画面、声音和说话内容。</p>
            </div>
          </div>
          <div
            className="material-tabs"
            role="tablist"
            aria-label="选择核验方式"
          >
            {(
              [
                ["general", "audio", "语音 / 视频 / 照片"],
                ["chat", "chat", "聊天截图"],
              ] as const
            ).map(([s, icon, label]) => (
              <button
                role="tab"
                id={"mode-" + s}
                aria-controls="material-panel"
                tabIndex={scene === s ? 0 : -1}
                onKeyDown={(e) => {
                  if (
                    busy ||
                    !["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)
                  )
                    return;
                  e.preventDefault();
                  const next =
                    e.key === "Home"
                      ? "general"
                      : e.key === "End"
                        ? "chat"
                        : scene === "general"
                          ? "chat"
                          : "general";
                  setScene(next);
                  setFiles([]);
                  setSelected(0);
                  setError("");
                  requestAnimationFrame(() =>
                    document.getElementById("mode-" + next)?.focus(),
                  );
                }}
                aria-selected={scene === s}
                className={scene === s ? "active" : ""}
                key={s}
                disabled={busy}
                onClick={() => {
                  setScene(s);
                  setFiles([]);
                  setSelected(0);
                  setError("");
                }}
              >
                <Icon name={icon} />
                {label}
              </button>
            ))}
          </div>
          <div
            role="tabpanel"
            id="material-panel"
            aria-labelledby={"mode-" + scene}
          >
            <label
              className={
                "drop " + (drag ? "dragging " : "") + (busy ? "disabled" : "")
              }
              onDragOver={(e) => {
                e.preventDefault();
                if (!busy) setDrag(true);
              }}
              onDragLeave={() => setDrag(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDrag(false);
                choose(e.dataTransfer.files);
              }}
            >
              <input
                ref={picker}
                type="file"
                multiple
                aria-label={
                  scene === "chat" ? "选择聊天截图" : "选择视频、语音或照片"
                }
                disabled={busy}
                accept={
                  scene === "chat"
                    ? ".jpg,.jpeg,.png,.webp"
                    : ".mp4,.mov,.avi,.webm,.wav,.mp3,.m4a,.flac,.ogg,.jpg,.jpeg,.png,.webp"
                }
                onChange={(e) => choose(e.target.files)}
              />
              <Icon name="upload" />
              <strong>
                {drag
                  ? "松开，添加材料"
                  : scene === "chat"
                    ? "上传聊天截图"
                    : "拖放文件，或点击上传"}
              </strong>
              <span>
                {scene === "chat"
                  ? "提取原话，核实对方提出的要求"
                  : "语音 · 视频 · 照片"}
              </span>
              <small>每次最多4份 · 单份≤100MB · 视频≤3分钟</small>
            </label>
            {!!files.length && (
              <>
                <ul className="file-list">
                  {files.map((f, i) => (
                    <li key={f.name + "-" + i}>
                      <Icon
                        name={
                          f.type.startsWith("video")
                            ? "video"
                            : f.type.startsWith("audio")
                              ? "audio"
                              : scene === "chat"
                                ? "chat"
                                : "image"
                        }
                      />
                      <div>
                        <button
                          className="text-button"
                          style={{
                            padding: 0,
                            minHeight: 28,
                            maxWidth: "100%",
                          }}
                          onClick={() => setSelected(i)}
                          aria-pressed={selected === i}
                        >
                          <strong>{f.name}</strong>
                        </button>
                        <small>
                          {(f.size / 1048576).toFixed(2)} MB
                          {busy
                            ? " · " +
                              (i < batchIndex
                                ? "已完成"
                                : i === batchIndex
                                  ? "正在核验"
                                  : "等待中")
                            : ""}
                        </small>
                      </div>
                      <button
                        className="icon-button"
                        disabled={busy}
                        aria-label={"移除" + f.name}
                        onClick={() => {
                          setFiles((fs) => fs.filter((_, j) => j !== i));
                          setSelected(0);
                        }}
                      >
                        <Icon name="close" />
                      </button>
                    </li>
                  ))}
                </ul>
                {preview && (
                  <div className="preview">
                    {kind === "video" ? (
                      <video src={preview} controls preload="metadata" />
                    ) : kind === "audio" ? (
                      <audio src={preview} controls preload="metadata" />
                    ) : (
                      <img src={preview} alt="待核验的材料预览" />
                    )}
                  </div>
                )}
              </>
            )}
            <button
              className="primary wide"
              disabled={!files.length || busy}
              onClick={() => void submit()}
            >
              {busy
                ? "正在核验 " +
                  (batchIndex + 1) +
                  " / " +
                  Math.max(files.length, 1)
                : "开始核验" +
                  (files.length > 1 ? "这" + files.length + "份材料" : "")}
              <Icon name="arrow" />
            </button>
            <p className="privacy-line">
              <Icon name="shield" />{" "}
              由部署电脑处理，上传副本处理后删除。报告与转写可在记录中删除。
            </p>
            {busy && (
              <div className="progress">
                <div role="status" aria-live="polite">
                  <span className="spinner" />
                  {message}
                </div>
                <small>已等待 {elapsed} 秒 · 不同材料和首次加载耗时不同</small>
                <ol className="processing-stages">
                  {(scene === "chat"
                    ? [
                        "提交截图",
                        "提取聊天文字",
                        "核实可疑要求",
                        "整理核验报告",
                      ]
                    : kind === "image"
                      ? [
                          "提交照片",
                          "检查图片合成线索",
                          "整理检测依据",
                          "整理核验报告",
                        ]
                      : kind === "audio"
                        ? [
                            "提交录音",
                            "检查声音合成线索",
                            "转写并核实内容",
                            "整理核验报告",
                          ]
                        : [
                            "提交视频",
                            "分别检查画面与声音",
                            "转写并核实内容",
                            "整理核验报告",
                          ]
                  ).map((label, i) => (
                    <li
                      key={label}
                      className={
                        i < stage ? "done" : i === stage ? "current" : ""
                      }
                    >
                      <b>{i < stage ? "✓" : i + 1}</b>
                      {label}
                    </li>
                  ))}
                </ol>
                <p className="privacy-line">
                  可以切换页面。当前任务会继续，完成后在核验记录查看。
                </p>
                {files.length > 1 && (
                  <button
                    className="quiet"
                    onClick={() => {
                      stopRef.current = true;
                      setStop(true);
                    }}
                    disabled={stop}
                  >
                    {stop ? "本份完成后停止后续提交" : "完成本份后停止"}
                  </button>
                )}
              </div>
            )}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
          </div>
        </article>
        <aside className="right-column">
          <article className="notice">
            <span className="pill">涉及钱的事，先停一下</span>
            <h2>
              再像的声音，
              <br />
              也值得再确认。
            </h2>
            <p>别用可疑消息里刚发来的号码。请联系事先确认并保存的家人。</p>
            <button className="primary wide" onClick={onContacts}>
              联系我的家人 <Icon name="up" />
            </button>
          </article>
          <article className="card workflow">
            <h2>你会看到什么？</h2>
            {[
              [
                "1",
                "材料有哪些线索",
                "画面和声音分开判断，不混成一个真假概率。",
              ],
              [
                "2",
                "原话提出了什么要求",
                "核对转写文字，查看风险要求与公开资料。",
              ],
              ["3", "下一步怎么核实", "依据本次结果提问，再联系可信的人。"],
            ].map(([n, t, p]) => (
              <div className="workflow-row" key={n}>
                <span>0{n}</span>
                <div>
                  <h3>{t}</h3>
                  <p>{p}</p>
                </div>
              </div>
            ))}
            <p className="muted">没有检出合成线索，不等于身份真实。</p>
          </article>
        </aside>
      </div>
    </>
  );
}
