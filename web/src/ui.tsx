import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
const paths: Record<string, ReactNode> = {
  lens: (
    <>
      <circle cx="11" cy="11" r="7.5" />
      <circle cx="11" cy="11" r="3" />
      <path d="m17 17 5 5" />
    </>
  ),
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  up: <path d="M5 19 19 5H6m13 0v13" />,
  audio: (
    <>
      <rect x="9" y="3" width="6" height="12" rx="3" />
      <path d="M5 11v1a7 7 0 0 0 14 0v-1M12 19v3m-3 0h6" />
    </>
  ),
  video: (
    <>
      <rect x="2" y="5" width="14" height="14" rx="3" />
      <path d="m16 10 6-4v12l-6-4" />
    </>
  ),
  image: (
    <>
      <rect x="3" y="3" width="18" height="18" rx="3" />
      <circle cx="8" cy="8" r="1" />
      <path d="m3 16 6-5 4 4 3-3 5 5" />
    </>
  ),
  chat: (
    <>
      <path d="M5 4h14a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H9l-6 4V6a2 2 0 0 1 2-2Z" />
      <path d="M7 9h10M7 13h6" />
    </>
  ),
  heart: <path d="M12 21 3 12A5.7 5.7 0 0 1 12 5a5.7 5.7 0 0 1 9 7Z" />,
  book: (
    <>
      <path d="M3 4h7a3 3 0 0 1 2 1 3 3 0 0 1 2-1h7v16h-7a3 3 0 0 0-2 1 3 3 0 0 0-2-1H3Z" />
      <path d="M12 5v16" />
    </>
  ),
  history: (
    <>
      <path d="M3 10a9 9 0 1 1 0 5M3 4v6h6M12 7v6l4 2" />
    </>
  ),
  shield: (
    <>
      <path d="m12 2 9 4v6c0 5-9 10-9 10S3 17 3 12V6Z" />
      <path d="m8 12 3 3 5-6" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5" />
    </>
  ),
  close: <path d="m6 6 12 12M6 18 18 6" />,
  menu: <path d="M3 6h18M3 12h18M3 18h18" />,
  settings: (
    <>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 1v3m0 16v3M1 12h3m16 0h3M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2" />
    </>
  ),
  play: <path d="m8 4 12 8-12 8Z" />,
  pause: <path d="M8 4v16M16 4v16" />,
  check: <path d="m4 12 5 5L20 6" />,
  plus: <path d="M12 4v16M4 12h16" />,
  phone: <path d="m5 3 5 4-3 4 6 6 4-3 4 5-3 3C10 22 2 14 2 6Z" />,
  help: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="M9 8a3 3 0 1 1 4 3c-1 1-1 2-1 3m0 3h.01" />
    </>
  ),
  download: <path d="M12 3v12m-5-5 5 5 5-5M3 17v5h18v-5" />,
};
export function Icon({
  name,
  className = "",
}: {
  name: string;
  className?: string;
}) {
  return (
    <svg
      className={"icon " + className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] || paths.lens}
    </svg>
  );
}
export function Dialog({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    const old = document.activeElement as HTMLElement | null;
    d?.showModal();
    const before = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      d?.close();
      document.body.style.overflow = before;
      old?.focus();
    };
  }, []);
  return (
    <dialog
      ref={ref}
      className="modal"
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
      aria-label={title}
    >
      <div className="modal-head">
        <span className="eyebrow">TRUTHLENS / 真鉴</span>
        <button className="icon-button" onClick={onClose} aria-label="关闭弹窗">
          <Icon name="close" />
        </button>
      </div>
      <h2>{title}</h2>
      {children}
    </dialog>
  );
}
export const errorText = (e: unknown) =>
  e instanceof Error ? e.message : "暂时未能完成，请重试。";

export function focusQuestions() {
  const el = document.getElementById("report-question-title");
  el?.scrollIntoView({
    behavior:
      document.documentElement.dataset.motion === "off" ? "auto" : "smooth",
    block: "start",
  });
  el?.focus({ preventScroll: true });
}
