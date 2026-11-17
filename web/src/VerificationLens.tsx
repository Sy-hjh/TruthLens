import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";

const source = "/hero-magnifier-v2.jpg";
const width = 1920;
const height = 712;
const portraitPhoto = { x: 0.577, y: 0.651 };
const mouth = { x: 0.716, y: 0.512 };
const wave = [10, 17, 33, 65, 41, 82, 58, 31, 14, 9, 20, 48, 74, 51, 37, 18, 8];

export default function VerificationLens() {
  const layer = useRef<HTMLDivElement>(null);
  const cover = useRef<HTMLImageElement>(null);
  const drag = useRef<{ id: number; dx: number; dy: number } | null>(null);
  const [position, setPosition] = useState(portraitPhoto);
  const [surface, setSurface] = useState({ width: 0, height: 0, left: 0, top: 0, frameWidth: 0, frameHeight: 0 });

  useEffect(() => {
    const frame = layer.current;
    const image = cover.current;
    if (!frame || !image) return;
    const update = () => {
      const { width: frameWidth, height: frameHeight } = frame.getBoundingClientRect();
      const scale = Math.max(frameWidth / width, frameHeight / height);
      const imageWidth = width * scale;
      const imageHeight = height * scale;
      const [horizontal, vertical] = getComputedStyle(image).objectPosition.split(" ");
      setSurface({
        width: imageWidth,
        height: imageHeight,
        left: (frameWidth - imageWidth) * (parseFloat(horizontal) / 100),
        top: (frameHeight - imageHeight) * (parseFloat(vertical) / 100),
        frameWidth,
        frameHeight,
      });
    };
    const observer = new ResizeObserver(update);
    observer.observe(frame);
    update();
    return () => observer.disconnect();
  }, []);

  const { x, y } = position;
  const positionX = surface.left + x * surface.width;
  const positionY = surface.top + y * surface.height;
  const overMouth = Math.hypot((x - mouth.x) / 0.04, (y - mouth.y) / 0.065) < 1;
  const overPhoto = x >= 0.52 && x <= 0.628 && y >= 0.54 && y <= 0.80;
  const clue = overMouth ? "audio" : overPhoto ? "image" : "none";

  function place(left: number, top: number) {
    setPosition({
      x: (Math.max(24, Math.min(surface.frameWidth - 26, left)) - surface.left) / surface.width,
      y: (Math.max(24, Math.min(surface.frameHeight - 26, top)) - surface.top) / surface.height,
    });
  }

  function start(event: PointerEvent<HTMLButtonElement>) {
    const bounds = layer.current?.getBoundingClientRect();
    if (!event.isPrimary || event.button !== 0 || !bounds) return;
    drag.current = { id: event.pointerId,
      dx: event.clientX - bounds.left - positionX,
      dy: event.clientY - bounds.top - positionY };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
    event.currentTarget.focus({ preventScroll: true });
  }

  function move(event: PointerEvent<HTMLButtonElement>) {
    const active = drag.current;
    const bounds = layer.current?.getBoundingClientRect();
    if (active?.id !== event.pointerId || !bounds) return;
    place(event.clientX - bounds.left - active.dx, event.clientY - bounds.top - active.dy);
  }

  function moveByKey(event: KeyboardEvent<HTMLButtonElement>) {
    switch (event.key) {
      case "ArrowLeft": place(positionX - 14, positionY); break;
      case "ArrowRight": place(positionX + 14, positionY); break;
      case "ArrowUp": place(positionX, positionY - 14); break;
      case "ArrowDown": place(positionX, positionY + 14); break;
      default: return;
    }
    event.preventDefault();
  }

  return (
    <>
      <img ref={cover} className="hero-photo magnifier-cover" src={source} width={width} height={height} fetchPriority="high"
        alt="AI 生成演示：封面中的女生一边说话，一边举着一张照片" draggable={false} />
      <div className="cover-magnifier-layer" ref={layer}>
        <span className="cover-magnifier-disclosure">AI 生成演示</span>
        {surface.width > 0 && (
          <button type="button" className="cover-magnifier" data-clue={clue}
            style={{ left: positionX, top: positionY }}
            title="拖动放大镜到嘴边或照片上"
            aria-label="拖动放大镜，或用方向键移动到嘴边和照片上"
            onKeyDown={moveByKey} onPointerDown={start} onPointerMove={move}
            onLostPointerCapture={() => { drag.current = null; }}>
            <span className="cover-magnifier-glass" aria-hidden="true">
              {clue === "image" && (
                <span className="cover-magnifier-detail" style={{
                  backgroundImage: `url(${source})`,
                  backgroundSize: `${surface.width * 1.85}px ${surface.height * 1.85}px`,
                  backgroundPosition: `calc(50% + ${(0.5 - x) * surface.width * 1.85}px) calc(50% + ${(0.5 - y) * surface.height * 1.85}px)`,
                }} />
              )}
              {clue === "audio" && (
                <span className="cover-magnifier-wave">
                  {wave.map((bar, i) => <span key={i} style={{ height: `${bar}%` }} />)}
                </span>
              )}
            </span>
          </button>
        )}
      </div>
    </>
  );
}
