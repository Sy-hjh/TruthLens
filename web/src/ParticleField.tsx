import { useEffect, useRef } from "react";

/** Decorative only: no media, detection scores or user data enter this canvas. */
export default function ParticleField({ motion }: { motion: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const el = canvas.current;
    const host = el?.closest<HTMLElement>(".hero");
    const ctx = el?.getContext("2d", { alpha: true });
    if (!el || !host || !ctx) return;
    let width = 1,
      height = 1,
      frame = 0,
      last = 0,
      visible = true;
    let pointer = { x: -1000, y: -1000 };
    let ripples: { x: number; y: number; born: number }[] = [];
    const seeds = Array.from({ length: 76 }, (_, i) => ({
      x: (i * 0.61803398875) % 1,
      y: (i * 0.41421356 + 0.13) % 1,
      phase: i * 2.39996,
      radius: i % 7 === 0 ? 2.2 : 1,
    }));
    const draw = (time: number) => {
      ctx.clearRect(0, 0, width, height);
      const t = motion ? time * 0.00016 : 0;
      const count = width < 600 ? 30 : seeds.length;
      const nodes = seeds.slice(0, count).map((s) => {
        let x = s.x * width + Math.sin(t + s.phase) * 24;
        let y = s.y * height + Math.cos(t * 0.8 + s.phase) * 20;
        const dx = x - pointer.x,
          dy = y - pointer.y,
          dist = Math.hypot(dx, dy);
        if (motion && dist > 0 && dist < 145) {
          x += (dx / dist) * (145 - dist) * 0.2;
          y += (dy / dist) * (145 - dist) * 0.2;
        }
        return { x, y, radius: s.radius };
      });
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j],
            dist = Math.hypot(a.x - b.x, a.y - b.y);
          if (dist < 140) {
            ctx.strokeStyle = `rgba(219,255,148,${(1 - dist / 140) * 0.18})`;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
        ctx.fillStyle = "rgba(226,255,166,0.65)";
        ctx.beginPath();
        ctx.arc(a.x, a.y, a.radius, 0, Math.PI * 2);
        ctx.fill();
      }
      // Low-contrast field contours: a designed visual, not a detection heatmap.
      for (let k = 0; k < 4; k++) {
        ctx.beginPath();
        for (let x = 0; x <= width; x += 14) {
          const y =
            height * 0.84 +
            Math.sin((x / width) * 5 + t + k * 0.17) * height * 0.09 +
            k * 12;
          if (!x) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = `rgba(219,255,72,${0.13 - k * 0.022})`;
        ctx.stroke();
      }
      ripples = ripples.filter((r) => time - r.born < 1000);
      for (const r of ripples) {
        const age = Math.max(0, (time - r.born) / 1000);
        ctx.strokeStyle = `rgba(219,255,72,${(1 - age) * 0.55})`;
        ctx.beginPath();
        ctx.arc(r.x, r.y, 12 + age * 160, 0, Math.PI * 2);
        ctx.stroke();
      }
    };
    const resize = () => {
      width = host.clientWidth;
      height = host.clientHeight;
      const dpr = Math.min(devicePixelRatio || 1, 1.5);
      el.width = width * dpr;
      el.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw(performance.now());
    };
    const move = (e: PointerEvent) => {
      if (!motion || e.pointerType === "touch") return;
      const b = host.getBoundingClientRect();
      pointer = { x: e.clientX - b.left, y: e.clientY - b.top };
      host.style.setProperty("--pointer-x", `${pointer.x}px`);
      host.style.setProperty("--pointer-y", `${pointer.y}px`);
    };
    const leave = () => {
      pointer = { x: -1000, y: -1000 };
    };
    const click = (e: PointerEvent) => {
      if (!motion || (e.target as HTMLElement).closest("button,a,.lens-widget"))
        return;
      const b = host.getBoundingClientRect();
      ripples.push({
        x: e.clientX - b.left,
        y: e.clientY - b.top,
        born: performance.now(),
      });
      ripples = ripples.slice(-4);
    };
    const ro = new ResizeObserver(resize);
    ro.observe(host);
    const io = new IntersectionObserver((entries) => {
      visible = entries[0].isIntersecting;
    });
    io.observe(host);
    host.addEventListener("pointermove", move, { passive: true });
    host.addEventListener("pointerleave", leave);
    host.addEventListener("pointerdown", click);
    const tick = (time: number) => {
      frame = requestAnimationFrame(tick);
      if (document.hidden || !visible || time - last < 33) return;
      last = time;
      draw(time);
    };
    resize();
    if (motion) frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      ro.disconnect();
      io.disconnect();
      host.removeEventListener("pointermove", move);
      host.removeEventListener("pointerleave", leave);
      host.removeEventListener("pointerdown", click);
      host.style.removeProperty("--pointer-x");
      host.style.removeProperty("--pointer-y");
    };
  }, [motion]);
  return (
    <div className="particle-atmosphere" aria-hidden="true">
      <div className="aurora aurora-a" />
      <div className="aurora aurora-b" />
      <div className="pointer-halo" />
      <canvas ref={canvas} />
    </div>
  );
}
