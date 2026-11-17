import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { CompanionJob } from "./CompanionVerification";
import type { ClipboardEvent, ReactNode } from "react";
import { Icon, errorText } from "./ui";

type Recording = "question" | "audio" | "screen";
type Capture = Recording | "snapshot";
const imageFormats = ".jpg,.jpeg,.png,.webp";
const formats = {
  audio: ".wav,.mp3,.m4a,.flac,.ogg",
  video: ".mp4,.mov,.avi,.webm",
  image: imageFormats,
  chat: imageFormats,
};
export type MaterialKind = keyof typeof formats;
const acceptedFormats = [...new Set(Object.values(formats))].join(",");
const isImage = (file: File) => /\.(jpg|jpeg|png|webp)$/i.test(file.name);

export default function CompanionMedia({
  onTranscript,
  disabled,
  materialKind,
  materialOptions,
  question,
  conversationContext,
  onAttachmentSent,
  renderComposer,
}: {
  onTranscript: (text: string) => void;
  disabled: boolean;
  materialKind: MaterialKind | "any" | null;
  materialOptions: MaterialKind[];
  question: string;
  conversationContext: string;
  onAttachmentSent: (question: string, job: CompanionJob) => void;
  renderComposer: (
    controls: ReactNode,
    attachment: { send: () => void; disabled: boolean } | null,
    onPaste: (event: ClipboardEvent<HTMLFormElement>) => void,
  ) => ReactNode;
}) {
  const [capture, setCapture] = useState<Capture | null>(null);
  const [material, setMaterial] = useState<{ file: File; capture?: "audio" | "screen" } | null>(null);
  const [preview, setPreview] = useState("");
  const [chat, setChat] = useState(false);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const active = useRef<AbortController | null>(null);
  const picker = useRef<HTMLInputElement>(null);
  const stop = useRef<(() => void) | null>(null);
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      active.current?.abort();
      stop.current?.();
    };
  }, []);

  useEffect(() => {
    if (!material) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(material.file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [material]);

  function attach(file: File) {
    setError("");
    if (!acceptedFormats.split(",").includes(file.name.slice(file.name.lastIndexOf(".")).toLowerCase()) ||
      !file.size || file.size > 100 * 1024 * 1024) {
      setError("请选择不超过100MB的图片、视频或音频文件。");
      return;
    }
    setStatus("");
    setChat(isImage(file) && materialKind === "chat");
    setMaterial({ file });
  }

  async function screenshot() {
    setError("");
    setStatus("在浏览器的选择框里选你想截屏的窗口或标签页。");
    setCapture("snapshot");
    const video = document.createElement("video");
    let timer: number | undefined;
    let stream: MediaStream | undefined;
    try {
      stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false });
      if (!mounted.current) return;
      stop.current = () => stream?.getTracks().forEach((track) => track.stop());
      video.muted = true;
      video.playsInline = true;
      video.srcObject = stream;
      await Promise.race([
        video.play(),
        new Promise<never>((_, reject) => {
          timer = window.setTimeout(() => reject(Error("截图等待超时")), 8000);
        }),
      ]);
      if (!video.videoWidth || !video.videoHeight) throw Error("没有可截图的画面");
      const scale = Math.min(1, 4096 / Math.max(video.videoWidth, video.videoHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
      canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
      const context = canvas.getContext("2d");
      if (!context) throw Error("无法生成截图");
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      stream.getTracks().forEach((track) => track.stop());
      const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/png"));
      if (!blob) throw Error("无法生成截图");
      if (mounted.current) attach(new File([blob], "截图.png", { type: "image/png" }));
    } catch {
      if (mounted.current) {
        setError("未取得截图，可用「添加附件」选择图片。");
        setStatus("");
      }
    } finally {
      window.clearTimeout(timer);
      stream?.getTracks().forEach((track) => track.stop());
      stop.current = null;
      video.srcObject = null;
      if (mounted.current) setCapture(null);
    }
  }

  async function transcribeQuestion(blob: Blob, extension: string) {
    if (!blob.size || blob.size > 10 * 1024 * 1024) {
      setStatus("");
      setError("没能取得这段语音，请再试一次或直接打字。");
      return;
    }
    setBusy(true);
    setStatus("正在识别语音…");
    const controller = new AbortController();
    active.current = controller;
    try {
      const form = new FormData();
      form.append("file", blob, `question.${extension}`);
      const { text } = await api<{ text: string }>("/api/companion/transcribe", {
        method: "POST",
        body: form,
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(90000)]),
      }, 90000);
      if (controller.signal.aborted) return;
      onTranscript(text);
      setStatus("已填入输入框，确认文字后发送。");
    } catch (e) {
      if (!controller.signal.aborted) {
        setStatus("");
        setError(errorText(e));
      }
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  async function record(kind: Recording) {
    setError("");
    setStatus(kind === "screen" ? "在浏览器的选择框里选你想录制的窗口或标签页。" : "等待浏览器授权…");
    setCapture(kind);
    let stream: MediaStream | undefined;
    try {
      stream = kind === "screen"
        ? await navigator.mediaDevices.getDisplayMedia({ video: true, audio: true })
        : await navigator.mediaDevices.getUserMedia({ audio: true });
      if (!mounted.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      const recorder = new MediaRecorder(stream);
      const tracks = stream.getTracks();
      const chunks: Blob[] = [];
      const noAudio = kind === "screen" && !stream.getAudioTracks().length;
      const finish = () => {
        if (recorder.state !== "inactive") recorder.stop();
        tracks.forEach((track) => track.stop());
      };
      const timer = window.setTimeout(finish, kind === "question" ? 30000 : 120000);
      stop.current = finish;
      tracks.forEach((track) => track.addEventListener("ended", finish, { once: true }));
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onerror = () => finish();
      recorder.onstop = () => {
        clearTimeout(timer);
        tracks.forEach((track) => track.stop());
        stop.current = null;
        if (!mounted.current) return;
        setCapture(null);
        const type = recorder.mimeType || chunks[0]?.type || "";
        const ext = type.includes("mp4") ? kind === "screen" ? "mp4" : "m4a"
          : type.includes("ogg") ? "ogg" : "webm";
        if (kind === "question") {
          void transcribeQuestion(new Blob(chunks, { type }), ext);
          return;
        }
        const file = new File(chunks, (kind === "screen" ? "录屏" : "录音") + "." + ext, { type });
        if (!file.size || file.size > 100 * 1024 * 1024) {
          setStatus("");
          setError("录制内容为空或超过100MB，请重录或选文件。");
          return;
        }
        setMaterial({ file, capture: kind });
        setChat(false);
        setStatus(noAudio ? "这段录屏没有音轨。可以核验画面，或选择带声音的原文件。" : "");
      };
      recorder.start();
      setStatus(kind === "screen" ? "正在录屏…" : "正在录音…");
    } catch {
      stream?.getTracks().forEach((track) => track.stop());
      if (mounted.current) {
        setStatus("");
        setCapture(null);
        setError(kind === "question" ? "无法使用麦克风，可以打字输入。" : "未能录制，可以直接选文件。");
      }
    }
  }

  async function submit() {
    if (disabled || busy || !material) return;
    setBusy(true);
    setError("");
    setStatus("正在提交…");
    const controller = new AbortController();
    active.current = controller;
    try {
      const form = new FormData();
      form.append("file", material.file);
      const request = {
        method: "POST",
        body: form,
        signal: AbortSignal.any([controller.signal, AbortSignal.timeout(90000)]),
      };
      form.append("scene", chat ? "chat" : "general");
      if (material.capture === "audio" || (material.file.type.startsWith("audio/") && /\.webm$/i.test(material.file.name))) {
        form.append("audio_only", "true");
      }
      const description = question.trim();
      const context = [conversationContext, description].filter(Boolean).join("\n");
      if (context) form.append("context", context);
      const { job_id } = await api<{ job_id: string }>("/api/analyze", request, 90000);
      onAttachmentSent(description, { id: job_id, filename: material.file.name });
    } catch (e) {
      if (!controller.signal.aborted) {
        setStatus("");
        setError(errorText(e));
      }
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }

  const image = !!material && isImage(material.file);
  const audio = !!material && (material.capture === "audio" ||
    material.file.type.startsWith("audio/") || /\.(wav|mp3|m4a|flac|ogg)$/i.test(material.file.name));
  const locked = disabled || busy || !!capture;
  const canRecord = typeof MediaRecorder !== "undefined";
  const recordAudio = materialOptions.includes("audio");
  const attachment = material
    ? { send: () => void submit(), disabled: locked }
    : null;
  return (
    <section aria-label="给小鉴提供材料">
      <div className="companion-tools" hidden={!recordAudio && capture !== "audio"}>
        {recordAudio && <button type="button" disabled={locked || !canRecord || !navigator.mediaDevices?.getUserMedia}
          onClick={() => void record("audio")}>录制待核验声音</button>}
        {capture === "audio" && <button type="button" disabled={!stop.current} onClick={() => stop.current?.()}>停止录制</button>}
      </div>
      <input hidden ref={picker} type="file" accept={acceptedFormats}
        onChange={(event) => {
          const file = event.currentTarget.files?.[0];
          event.currentTarget.value = "";
          if (file && !locked) attach(file);
        }} />
      {material && !capture && (
        <div className="companion-answer">
          <p>{material.file.name}</p>
          {preview && (image ? <img src={preview} alt="待核验图片" style={{ maxWidth: "100%", maxHeight: 150 }} />
            : audio ? <audio controls src={preview} style={{ maxWidth: "100%" }} />
              : <video controls src={preview} style={{ maxWidth: "100%", maxHeight: 170 }} />)}
          {image && (
            <label><input type="checkbox" checked={chat} disabled={locked}
              onChange={(event) => setChat(event.target.checked)} /> 核验截图里的聊天内容</label>
          )}
          <div className="companion-tools">
            <button type="button" disabled={locked} onClick={() => {
              setMaterial(null);
              setStatus("");
              setError("");
            }}>移除</button>
          </div>
        </div>
      )}
      {renderComposer(
        <>
          <button type="button" className="companion-mic" aria-label="添加附件" title="添加附件"
            disabled={locked} onClick={() => picker.current?.click()}>
            <Icon name="plus" />
          </button>
          <button type="button" className="companion-mic companion-capture" aria-label="截屏"
            title="先打开想截的窗口，再点截屏" disabled={locked || !navigator.mediaDevices?.getDisplayMedia}
            onClick={() => void screenshot()}>
            <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" aria-hidden="true">
              <circle cx="6" cy="6" r="3" /><circle cx="6" cy="18" r="3" />
              <path d="m8.2 8.2 4.5 4.5m2.8 2.8L20 20M8.2 15.8 20 4" />
            </svg>
          </button>
          <button type="button" className="companion-mic companion-capture companion-record"
            aria-label={capture === "screen" ? "停止录屏" : "录屏"}
            title={capture === "screen" ? "停止录屏" : "先打开想录的窗口，再点录屏"}
            disabled={capture === "screen" ? !stop.current : locked || !canRecord || !navigator.mediaDevices?.getDisplayMedia}
            onClick={() => capture === "screen" ? stop.current?.() : void record("screen")}>
            <svg className="icon" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              {capture === "screen" ? <rect x="6" y="6" width="12" height="12" rx="2" /> : <circle cx="12" cy="12" r="6.5" />}
            </svg>
          </button>
          <button
            type="button"
            className="companion-mic"
            aria-label="说给小鉴听"
            title="说给小鉴听"
            disabled={locked || !!attachment || !canRecord || !navigator.mediaDevices?.getUserMedia}
            onClick={() => void record("question")}
          >
            <Icon name="audio" />
          </button>
          {capture === "question" && (
            <button
              type="button"
              className="companion-mic companion-stop"
              aria-label="停止录音"
              disabled={!stop.current}
              onClick={() => stop.current?.()}
            >
              停止
            </button>
          )}
        </>,
        attachment,
        (event) => {
          const file = event.clipboardData.files[0];
          if (file && !locked) {
            event.preventDefault();
            attach(file);
          }
        },
      )}
      {status && <p role="status">{status}</p>}
      {error && <p role="alert" className="error">{error}</p>}
    </section>
  );
}
