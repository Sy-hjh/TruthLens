import { useEffect, useRef } from "react";

export default function MotionLayer({
  motion,
  page,
}: {
  motion: boolean;
  page: string;
}) {
  const progress = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const update = () => {
      const max = document.documentElement.scrollHeight - innerHeight;
      progress.current?.style.setProperty(
        "--scroll",
        `${max > 0 ? scrollY / max : 0}`,
      );
    };
    let raf = 0;
    const scroll = () => {
      if (!raf)
        raf = requestAnimationFrame(() => {
          update();
          raf = 0;
        });
    };
    addEventListener("scroll", scroll, { passive: true });
    addEventListener("resize", scroll);
    const ro = new ResizeObserver(scroll);
    ro.observe(document.body);
    update();
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      removeEventListener("scroll", scroll);
      removeEventListener("resize", scroll);
    };
  }, [page]);
  useEffect(() => {
    if (!motion) return;
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries)
          if (e.isIntersecting) {
            e.target.classList.add("is-revealed");
            io.unobserve(e.target);
          }
      },
      { threshold: 0.08 },
    );
    const observed = new Set<HTMLElement>();
    const discover = () => {
      document
        .querySelectorAll<HTMLElement>(
          ".section-heading,.portal,.trust-strip>h2,.trust-steps>div,.workspace .card,.agent-panel",
        )
        .forEach((el, i) => {
          if (observed.has(el) || !el.getClientRects().length) return;
          observed.add(el);
          // Already visible content stays immediately usable; only future content enters.
          if (el.getBoundingClientRect().top < innerHeight * 0.96) return;
          el.classList.add("reveal-ready");
          el.style.setProperty("--reveal-delay", `${(i % 4) * 55}ms`);
          io.observe(el);
        });
    };
    discover();
    const mo = new MutationObserver(discover);
    mo.observe(document.getElementById("main-content")!, {
      childList: true,
      subtree: true,
    });
    let active: HTMLElement | null = null;
    const reset = () => {
      active?.style.removeProperty("--tilt-x");
      active?.style.removeProperty("--tilt-y");
      active = null;
    };
    const move = (e: PointerEvent) => {
      if (e.pointerType === "touch") return;
      const card = (e.target as HTMLElement).closest<HTMLElement>(".portal");
      if (active !== card) reset();
      if (!card) return;
      active = card;
      const b = card.getBoundingClientRect();
      card.style.setProperty(
        "--tilt-x",
        `${(-(e.clientY - b.top - b.height / 2) / b.height) * 6}deg`,
      );
      card.style.setProperty(
        "--tilt-y",
        `${((e.clientX - b.left - b.width / 2) / b.width) * 7}deg`,
      );
    };
    const ripple = (e: PointerEvent) => {
      const button = (e.target as HTMLElement).closest<HTMLElement>(
        "button.primary:not(:disabled)",
      );
      if (!button) return;
      const b = button.getBoundingClientRect(),
        ring = document.createElement("span");
      ring.className = "button-ripple";
      ring.setAttribute("aria-hidden", "true");
      ring.style.left = `${e.clientX - b.left}px`;
      ring.style.top = `${e.clientY - b.top}px`;
      button.append(ring);
      ring.addEventListener("animationend", () => ring.remove(), {
        once: true,
      });
    };
    document.addEventListener("pointermove", move, { passive: true });
    document.addEventListener("pointerdown", ripple);
    document.addEventListener("pointerleave", reset);
    return () => {
      io.disconnect();
      mo.disconnect();
      reset();
      observed.forEach((el) => {
        el.classList.remove("reveal-ready", "is-revealed");
        el.style.removeProperty("--reveal-delay");
      });
      document.querySelectorAll(".button-ripple").forEach((el) => el.remove());
      document.removeEventListener("pointermove", move);
      document.removeEventListener("pointerdown", ripple);
      document.removeEventListener("pointerleave", reset);
    };
  }, [motion, page]);
  return <div ref={progress} className="reading-progress" aria-hidden="true" />;
}
