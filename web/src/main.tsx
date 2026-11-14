import "./performance";
import MotionLayer from "./MotionLayer";
import Companion from "./Companion";
import MissionStage from "./MissionStage";
import ParticleField from "./ParticleField";
import { Component, Suspense, lazy, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import type { Report } from "./api";
import { Dialog, Icon } from "./ui";
import "./style.css";
const Upload = lazy(() => import("./views/Upload")),
  Contacts = lazy(() => import("./views/Contacts")),
  Practice = lazy(() => import("./views/Practice")),
  History = lazy(() => import("./views/History")),
  ReportView = lazy(() => import("./views/Report")),
  LensScene = lazy(() => import("./LensScene"));
type Page = "home" | "check" | "contacts" | "practice" | "history" | "report";
const routes = ["home", "check", "contacts", "practice", "history", "report"];
const nav = [
  ["check", "核验工作台", "lens"],
  ["contacts", "家人联系", "heart"],
  ["practice", "反诈课堂", "book"],
  ["history", "核验记录", "history"],
] as const;
function route(): Page {
  return routes.includes(location.hash.slice(1))
    ? (location.hash.slice(1) as Page)
    : "home";
}
function stored(key: string, fallback: string) {
  try {
    return localStorage.getItem(key) || fallback;
  } catch {
    return fallback;
  }
}
class Boundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <article className="card empty">
        <Icon name="help" />
        <h2>这一页暂时没有打开</h2>
        <p>已完成的报告仍在核验记录里。</p>
        <button className="primary" onClick={() => location.reload()}>
          重新打开
        </button>
      </article>
    ) : (
      this.props.children
    );
  }
}
function App() {
  const [page, setPage] = useState<Page>(route),
    [report, setReport] = useState<Report | null>(null),
    [bundle, setBundle] = useState<Report[]>([]),
    [menu, setMenu] = useState(false),
    [modal, setModal] = useState<"help" | "settings" | "privacy" | null>(null),
    [motion, setMotion] = useState(
      () => stored("truthlens-motion", "on") === "on",
    ),
    [large, setLarge] = useState(
      () => stored("truthlens-large", "off") === "on",
    ),
    [online, setOnline] = useState<boolean | null>(null),
    [sceneReady, setSceneReady] = useState(false);
  const heading = useRef<HTMLDivElement>(null);
  const currentPage = useRef(page);
  currentPage.current = page;
  const [checkVisited, setCheckVisited] = useState(page === "check");
  const [completedNotice, setCompletedNotice] = useState<{
    report: Report;
    all: Report[];
  } | null>(null);
  useEffect(() => {
    if (page === "check") setCheckVisited(true);
  }, [page]);
  const [reduced, setReduced] = useState(
    () => matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const effectiveMotion = motion && !reduced;
  useEffect(() => {
    const f = () => {
      if (routes.includes(location.hash.slice(1))) {
        setPage(route());
        setMenu(false);
      }
    };
    addEventListener("hashchange", f);
    api("/api/health")
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
    const id = setTimeout(() => setSceneReady(true), 1400);
    return () => {
      removeEventListener("hashchange", f);
      clearTimeout(id);
    };
  }, []);
  useEffect(() => {
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenu(false);
    };
    addEventListener("keydown", key);
    return () => removeEventListener("keydown", key);
  }, []);
  useEffect(() => {
    const media = matchMedia("(prefers-reduced-motion: reduce)");
    const change = () => setReduced(media.matches);
    media.addEventListener("change", change);
    const sync = (e: StorageEvent) => {
      if (e.key === "truthlens-motion") setMotion(e.newValue !== "off");
      if (e.key === "truthlens-large") setLarge(e.newValue === "on");
    };
    addEventListener("storage", sync);
    return () => {
      media.removeEventListener("change", change);
      removeEventListener("storage", sync);
    };
  }, []);
  useEffect(() => {
    document.documentElement.dataset.motion = effectiveMotion ? "on" : "off";
    document.documentElement.dataset.large = large ? "on" : "off";
    try {
      localStorage.setItem("truthlens-motion", motion ? "on" : "off");
      localStorage.setItem("truthlens-large", large ? "on" : "off");
    } catch {}
  }, [motion, large, reduced]);
  useEffect(() => {
    window.scrollTo({ top: 0 });
    if (page !== "home") heading.current?.focus();
    document.title =
      page === "home"
        ? "TruthLens 真鉴 · 面向亲友冒充的多模态核验与反诈问答"
        : (nav.find((n) => n[0] === page)?.[1] || "核验报告") +
          " · TruthLens 真鉴";
  }, [page]);
  function go(p: Page) {
    if (p === page) {
      window.scrollTo({ top: 0, behavior: "instant" });
      document.getElementById("main-content")?.focus({ preventScroll: true });
      return;
    }
    location.hash = p;
    setPage(p);
    setMenu(false);
  }
  function open(r: Report, all: Report[] = []) {
    setCompletedNotice(null);
    setReport(r);
    if (all.length) setBundle(all);
    else setBundle([]);
    try {
      sessionStorage.setItem("truthlens-last-report", r.id);
    } catch {}
    go("report");
  }
  function finishUpload(r: Report, all: Report[] = []) {
    dispatchEvent(new Event("truthlens:report-ready"));
    if (currentPage.current === "check") open(r, all);
    else setCompletedNotice({ report: r, all });
  }
  useEffect(() => {
    if (page === "report" && !report) {
      let id = "";
      try {
        id = sessionStorage.getItem("truthlens-last-report") || "";
      } catch {}
      if (id)
        api<Report>("/api/cases/" + id)
          .then(setReport)
          .catch(() => go("history"));
      else go("history");
    }
  }, [page, report]);
  return (
    <>
      <MotionLayer motion={effectiveMotion} page={page} />
      <Companion
        motion={effectiveMotion}
        page={page}
        report={page === "report" ? report : null}
        onNavigate={(p) => {
          if (routes.includes(p)) go(p as Page);
        }}
      />
      <a
        className="skip-link"
        href="#main-content"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        跳到主要内容
      </a>
      <header className="site-header">
        <a
          className="brand"
          href="#home"
          aria-label="TruthLens 真鉴首页"
          onClick={() => go("home")}
        >
          <span className="brand-symbol">
            <Icon name="lens" />
          </span>
          <span>
            TruthLens <b>真鉴</b>
          </span>
        </a>
        <nav
          className={menu ? "main-nav is-open" : "main-nav"}
          aria-label="主要功能"
        >
          {nav.map(([id, label]) => (
            <a
              href={"#" + id}
              className={page === id ? "active" : ""}
              aria-current={page === id ? "page" : undefined}
              key={id}
              onClick={() => go(id)}
            >
              {label}
            </a>
          ))}
        </nav>
        <div className="header-actions">
          <button
            className="icon-button settings-button"
            aria-label="打开使用偏好"
            onClick={() => setModal("settings")}
          >
            <Icon name="settings" />
          </button>
          <button className="primary header-cta" onClick={() => go("check")}>
            开始核验 <Icon name="up" />
          </button>
          <button
            className="icon-button mobile-menu"
            aria-label={menu ? "关闭导航菜单" : "打开导航菜单"}
            aria-expanded={menu}
            onClick={() => setMenu(!menu)}
          >
            <Icon name={menu ? "close" : "menu"} />
          </button>
        </div>
      </header>
      <main id="main-content" tabIndex={-1}>
        {page === "home" && (
          <>
            <section className="hero">
              <img
                className="hero-photo"
                src="/hero.jpg"
                width="1920"
                height="712"
                fetchPriority="high"
                alt="一位女士在家中查看手机消息"
              />
              <div className="hero-shade" />
              <ParticleField motion={effectiveMotion} />
              <div className="hero-content">
                <p className="eyebrow">
                  <span className="live-dot" /> TRUTHLENS / 让信任多一层依据
                </p>
                <h1>
                  看清伪装，
                  <br />
                  守住<span>信任。</span>
                </h1>
                <p className="hero-description">
                  声音很像，画面很真。
                  <br />
                  先核验，再用熟悉的号码确认。
                </p>
                <div className="hero-actions">
                  <button
                    className="primary hero-cta"
                    onClick={() => go("check")}
                  >
                    核验收到的消息 <Icon name="arrow" />
                  </button>
                  <button
                    className="text-button light"
                    onClick={() => setModal("help")}
                  >
                    <Icon name="play" /> 如何使用
                  </button>
                </div>
                <div className="hero-assurance">
                  <Icon name="shield" /> 独立核验 · 上传副本处理后删除
                </div>
              </div>
              <div className="hero-scene">
                {sceneReady && (
                  <Suspense fallback={null}>
                    <LensScene motion={effectiveMotion} />
                  </Suspense>
                )}
              </div>
              <div className="hero-bottom">
                <span>先停一下，再做决定。</span>
                <span>语音 / 图片 / 视频 / 聊天截图</span>
                <a href="#start" aria-label="向下查看功能入口">
                  向下探索 <span>↓</span>
                </a>
              </div>
            </section>
            <div className="home-mission">
              <MissionStage page="home" motion={effectiveMotion} />
            </div>
            <section className="portal-section" id="start">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">YOUR CIRCLE OF TRUST</p>
                  <h2>
                    从一个疑问，
                    <br />
                    到一次安心的确认。
                  </h2>
                </div>
                <p>
                  检查材料，读懂线索。
                  <br />
                  把下一步，交给值得信任的联系。
                </p>
              </div>
              <div className="portals">
                {nav.map(([id, label, icon], i) => (
                  <a
                    onPointerMove={(e) => {
                      if (!effectiveMotion || e.pointerType === "touch") return;
                      const b = e.currentTarget.getBoundingClientRect();
                      e.currentTarget.style.setProperty(
                        "--px",
                        e.clientX - b.left + "px",
                      );
                      e.currentTarget.style.setProperty(
                        "--py",
                        e.clientY - b.top + "px",
                      );
                    }}
                    className={"portal portal-" + id}
                    href={"#" + id}
                    key={id}
                    onClick={() => go(id)}
                  >
                    <div className="portal-top">
                      <span>
                        0{i + 1} / {label}
                      </span>
                      <Icon name="up" />
                    </div>
                    <div className="portal-art">
                      <Icon name={icon} />
                      <i />
                      <i />
                    </div>
                    <h3>
                      {
                        [
                          "这份消息，是真的吗？",
                          "联系熟悉的那个人",
                          "给自己，多一点识别力",
                          "每一次确认，都有迹可循",
                        ][i]
                      }
                    </h3>
                    <p>
                      {
                        [
                          "检查声音、照片、视频与聊天要求",
                          "保存可信号码，需要时独立回拨",
                          "情景练习与有来源的反诈预警",
                          "回看报告，与家人一起复核",
                        ][i]
                      }
                    </p>
                    <span className="portal-link">
                      {label} <Icon name="arrow" />
                    </span>
                  </a>
                ))}
              </div>
            </section>
            <section className="trust-strip">
              <p className="eyebrow">A LITTLE PAUSE. A BETTER DECISION.</p>
              <h2>
                核验，不是替你下结论。
                <br />
                是让你<span>有依据地判断。</span>
              </h2>
              <div className="trust-steps">
                {[
                  ["01", "检查材料", "分别寻找画面、声音中的合成线索。"],
                  ["02", "看懂要求", "提取原话，结合官方资料核实可疑套路。"],
                  ["03", "独立确认", "用原来保存的号码联系本人，再做决定。"],
                ].map(([n, h, p]) => (
                  <div key={n}>
                    <span>{n}</span>
                    <h3>{h}</h3>
                    <p>{p}</p>
                  </div>
                ))}
              </div>
              <button className="primary" onClick={() => go("check")}>
                开始一次核验 <Icon name="arrow" />
              </button>
            </section>
          </>
        )}
        <div className="workspace" hidden={page === "home"}>
          <div className="workspace-bar">
            <button className="text-button" onClick={() => go("home")}>
              ← 返回首页
            </button>
            <span>
              {page === "report"
                ? "核验报告"
                : nav.find((n) => n[0] === page)?.[1]}
            </span>
            <button className="text-button" onClick={() => setModal("help")}>
              使用帮助 <Icon name="help" />
            </button>
          </div>
          <div ref={heading} tabIndex={-1} className="page-focus" />
          {page !== "home" && (
            <MissionStage page={page} motion={effectiveMotion} />
          )}
          {(checkVisited || page === "check") && (
            <div hidden={page !== "check"} className="page-enter">
              <Boundary>
                <Suspense
                  fallback={
                    <p className="skeleton" role="status">
                      正在打开核验工作台…
                    </p>
                  }
                >
                  <Upload
                    onComplete={finishUpload}
                    onContacts={() => go("contacts")}
                  />
                </Suspense>
              </Boundary>
            </div>
          )}
          <Boundary key={page}>
            <Suspense
              fallback={
                <div className="skeleton" role="status">
                  正在打开页面…
                  <i />
                  <i />
                  <i />
                </div>
              }
            >
              {page === "check" || page === "home" ? null : page ===
                "contacts" ? (
                <Contacts />
              ) : page === "practice" ? (
                <Practice />
              ) : page === "history" ? (
                <History onOpen={open} />
              ) : report ? (
                <>
                  {bundle.length > 1 && (
                    <div className="bundle-tabs" aria-label="本次核验的材料">
                      {bundle.map((r, i) => (
                        <button
                          key={r.id}
                          aria-pressed={r.id === report.id}
                          onClick={() => setReport(r)}
                        >
                          {i + 1}. {r.filename}
                        </button>
                      ))}
                    </div>
                  )}
                  <ReportView
                    key={report.id}
                    report={report}
                    onContacts={() => go("contacts")}
                    onUpdate={(r) => {
                      setReport(r);
                      setBundle((bs) => bs.map((b) => (b.id === r.id ? r : b)));
                    }}
                  />
                </>
              ) : (
                <p role="status">正在读取报告…</p>
              )}
            </Suspense>
          </Boundary>
        </div>
      </main>
      {completedNotice && (
        <div className="completion-toast" role="status">
          <span>{completedNotice.all.length || 1}份材料已核验完成</span>
          <button
            onClick={() => {
              open(completedNotice.report, completedNotice.all);
              setCompletedNotice(null);
            }}
          >
            查看报告 →
          </button>
          <button
            className="icon-button"
            aria-label="关闭完成提醒"
            onClick={() => setCompletedNotice(null)}
          >
            <Icon name="close" />
          </button>
        </div>
      )}
      <footer className="site-footer">
        <div>
          <a className="brand" href="#home">
            <Icon name="lens" /> TruthLens 真鉴
          </a>
          <p>面向亲友冒充的多模态核验与反诈问答 Web系统</p>
        </div>
        <div>
          <button
            className="text-button light"
            onClick={() => setModal("privacy")}
          >
            隐私与数据
          </button>
          <button
            className="text-button light"
            onClick={() => setModal("settings")}
          >
            使用偏好
          </button>
          <span
            className={"service-state " + (online === false ? "offline" : "")}
          >
            <i />
            {online === null
              ? "正在连接服务"
              : online
                ? "核验服务已连接"
                : "服务暂未连接"}
          </span>
        </div>
        <small>检测提供线索，身份需要独立核实。</small>
      </footer>
      {modal && (
        <Dialog
          title={
            modal === "settings"
              ? "按你的习惯使用"
              : modal === "privacy"
                ? "你的材料，怎样被处理？"
                : "一次核验，三步就好"
          }
          onClose={() => setModal(null)}
        >
          {modal === "settings" ? (
            <>
              <div className="setting-row">
                <div>
                  <h3>动态效果</h3>
                  <p>粒子、立体透镜、滚动与悬停反馈</p>
                </div>
                <button
                  className="toggle"
                  role="switch"
                  aria-label="动态效果"
                  aria-checked={effectiveMotion}
                  onClick={() => setMotion(!motion)}
                >
                  {motion ? (reduced ? "系统减少" : "已开启") : "已关闭"}
                </button>
              </div>
              <div className="setting-row">
                <div>
                  <h3>大字模式</h3>
                  <p>放大功能页文字，阅读更轻松</p>
                </div>
                <button
                  className="toggle"
                  role="switch"
                  aria-label="大字模式"
                  aria-checked={large}
                  onClick={() => setLarge(!large)}
                >
                  {large ? "已开启" : "已关闭"}
                </button>
              </div>
              <p className="muted">
                系统设置“减少动态效果”时，会自动减少动画。
              </p>
            </>
          ) : modal === "privacy" ? (
            <div className="help-steps">
              <h3>原始图片、录音与视频</h3>
              <p>
                由部署系统的电脑处理，完成后删除上传副本，不会删除你设备上的原文件；不发送给云端大模型。手机访问时，材料会上传到部署本系统的电脑处理。
              </p>
              <h3>报告与转写文字</h3>
              <p>
                保存在这台电脑的核验记录里。你可以删除报告，同时清除对应反馈与核实步骤记录。
              </p>
              <h3>家人号码</h3>
              <p>只保存在当前浏览器，不提供给检测模型。请先和家人核对号码。</p>
            </div>
          ) : (
            <>
              <div className="help-steps">
                {[
                  [
                    "upload",
                    "上传收到的材料",
                    "选择录音、视频、照片；聊天截图请选专门入口。",
                  ],
                  [
                    "lens",
                    "查看结果与依据",
                    "看分项结果、时间片段与原话；无法判断会明确说明。",
                  ],
                  [
                    "phone",
                    "换个可信渠道确认",
                    "涉及钱、验证码或身份时，用已保存的号码联系本人。",
                  ],
                ].map(([i, h, p], n) => (
                  <div key={i}>
                    <span className="step">{n + 1}</span>
                    <div>
                      <h3>{h}</h3>
                      <p>{p}</p>
                    </div>
                  </div>
                ))}
              </div>
              <button
                className="primary wide"
                onClick={() => {
                  setModal(null);
                  go("check");
                }}
              >
                我知道了，开始核验 <Icon name="arrow" />
              </button>
            </>
          )}
        </Dialog>
      )}
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
