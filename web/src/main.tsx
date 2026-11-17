import "./performance";
import MotionLayer from "./MotionLayer";
import Companion from "./Companion";
import {
  CompanionProgress,
  CompanionReportAdvice,
  savedCompanionAdvice,
  savedCompanionJob,
  storeCompanionAdvice,
  storeCompanionJob,
} from "./CompanionVerification";
import type { CompanionJob } from "./CompanionVerification";
import MissionStage from "./MissionStage";
import ParticleField from "./ParticleField";
import VerificationLens from "./VerificationLens";
import { Component, Suspense, lazy, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import type { AccountSession, Report } from "./api";
import { Dialog, Icon } from "./ui";
import { AccountAccess } from "./AccountAccess";
import type { AccessMode } from "./AccountAccess";
import "./style.css";
const Upload = lazy(() => import("./views/Upload")),
  Contacts = lazy(() => import("./views/Contacts")),
  Practice = lazy(() => import("./views/Practice")),
  History = lazy(() => import("./views/History")),
  Admin = lazy(() => import("./views/Admin")),
  ReportView = lazy(() => import("./views/Report")),
  LensScene = lazy(() => import("./LensScene"));
type Page = "home" | "check" | "contacts" | "practice" | "history" | "report" | "admin";
const routes = ["home", "check", "contacts", "practice", "history", "report", "admin"];
const nav = [
  ["check", "核验工作台", "lens", "查看材料里的线索", "检查图片、声音、视频与聊天截图"],
  ["practice", "核验案例", "book", "了解不同场景怎么核实", "教学、电商、新闻、企业与日常生活"],
  ["history", "核验记录", "history", "回看每一次核验", "查看报告、依据和复核建议"],
] as const;
const homepageTitle = "真鉴 · AI 内容核验助手";
function pageTitle(page: Page) {
  if (page === "contacts") return "家人联系";
  if (page === "admin") return "管理后台";
  return nav.find(([id]) => id === page)?.[1] ?? "报告详情";
}
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
    [reportPreviews, setReportPreviews] = useState<Record<string, File>>({}),
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
  const [session, setSession] = useState<AccountSession | null>(null);
  const [authMode, setAuthMode] = useState<AccessMode | null>(null);
  const [authError, setAuthError] = useState("");
  const account = session?.account ?? null;
  const heading = useRef<HTMLDivElement>(null);
  const currentPage = useRef(page);
  currentPage.current = page;
  const [companionJob, setCompanionJob] = useState(savedCompanionJob);
  const [companionAdviceId, setCompanionAdviceId] = useState(savedCompanionAdvice);
  const activeCompanionJob = useRef(companionJob);
  activeCompanionJob.current = companionJob;
  const [checkVisited, setCheckVisited] = useState(page === "check");
  const [completedNotice, setCompletedNotice] = useState<{
    report: Report;
    all: Report[];
  } | null>(null);
  useEffect(() => {
    let active = true;
    void api<AccountSession>("/api/auth/session").then((value) => {
      if (active) setSession(value);
    }).catch(() => { if (active) setAuthError("暂时无法读取账号状态，请刷新后重试。"); });
    const needsLogin = () => {
      clearPrivateData();
      setSession((value) => value ? { ...value, account: null } : value);
      setAuthMode("login");
    };
    addEventListener("truthlens:auth-required", needsLogin);
    return () => { active = false; removeEventListener("truthlens:auth-required", needsLogin); };
  }, []);
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
    const timer = window.setTimeout(() => setSceneReady(true), 1400);
    return () => {
      removeEventListener("hashchange", f);
      window.clearTimeout(timer);
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
        ? homepageTitle
        : pageTitle(page) + " · 真鉴";
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
  function finishUpload(r: Report, all: Report[] = [], previews: Record<string, File> = {}) {
    setReportPreviews(previews);
    dispatchEvent(new Event("truthlens:report-ready"));
    if (currentPage.current === "check" && !activeCompanionJob.current) open(r, all);
    else setCompletedNotice({ report: r, all });
  }
  function trackCompanionJob(job: CompanionJob | null) {
    activeCompanionJob.current = job;
    setCompanionJob(job);
    storeCompanionJob(job);
    if (job) go("check");
  }
  function finishCompanionJob(result: Report) {
    trackCompanionJob(null);
    setCompanionAdviceId(result.id);
    storeCompanionAdvice(result.id);
    finishUpload(result);
  }
  function clearPrivateData() {
    activeCompanionJob.current = null;
    setCompanionJob(null);
    setCompanionAdviceId("");
    setReport(null);
    setBundle([]);
    setReportPreviews({});
    setCompletedNotice(null);
    storeCompanionJob(null);
    storeCompanionAdvice("");
    try {
      sessionStorage.removeItem("truthlens-last-report");
      sessionStorage.removeItem("qinan-active-job");
    } catch {}
  }
  async function logout() {
    try {
      await api("/api/auth/logout", { method: "POST" });
      clearPrivateData();
      setSession((value) => value ? { ...value, account: null } : value);
      setAuthError("");
      go("home");
    } catch { setAuthError("退出登录失败，请重试。"); }
  }
  useEffect(() => {
    if (page === "report" && !report && account) {
      let active = true;
      let id = "";
      try {
        id = sessionStorage.getItem("truthlens-last-report") || "";
      } catch {}
      if (id)
        api<Report>("/api/cases/" + id)
          .then((value) => { if (active) setReport(value); })
          .catch(() => { if (active) go("history"); });
      else go("history");
      return () => { active = false; };
    }
  }, [page, report, account]);

  const auth = authMode && <AccountAccess key={authMode} initialMode={authMode} setupRequired={session?.setup_required ?? false}
    close={() => setAuthMode(null)} onSuccess={(value) => {
      setSession({ account: value, setup_required: value.role === "admin" ? false : session?.setup_required ?? false });
      setAuthMode(null);
      setAuthError("");
      if (page === "admin" && value.role !== "admin") go("home");
      if (value.role === "admin" && (page === "admin" || authMode === "setup")) go("admin");
    }} />;
  const signIn = (
    <section className="card private-entry">
      <Icon name="shield" />
      <h1>{page === "admin" ? "真鉴管理后台" : page === "check" ? "登录后开始核验"
        : page === "contacts" ? "登录后查看家人联系" : "登录后查看报告"}</h1>
      {authError && <p className="error" role="alert">{authError}</p>}
      {account ? <><p>当前账号没有管理员权限。</p><a className="text-button" href="#home">← 返回用户端</a></> : (
        <div><button className="primary" onClick={() => setAuthMode("login")}>登录 <Icon name="arrow" /></button>
          {page === "admin" && session?.setup_required
            ? <button onClick={() => setAuthMode("setup")}>首次配置管理员</button>
            : <button onClick={() => setAuthMode("register")}>注册账号</button>}</div>
      )}
    </section>
  );
  if (page === "admin") {
    return <>{account?.role === "admin" ? (
      <Suspense fallback={<p className="skeleton" role="status">正在打开管理后台…</p>}>
        {authError && <p className="admin-message error" role="alert">{authError}</p>}
        <Admin account={account} onLogout={() => void logout()} />
      </Suspense>
    ) : <main className="admin-gate"><a href="#home">← 返回真鉴首页</a>{signIn}</main>}{auth}</>;
  }
  return (
    <>
      <MotionLayer motion={effectiveMotion} page={page} />
      <Companion
        key={account?.id ?? "guest"}
        authenticated={!!account}
        onAuthRequired={() => setAuthMode("login")}
        motion={effectiveMotion}
        page={page}
        report={page === "report" ? report : null}
        verificationPending={!!companionJob}
        onVerificationStart={trackCompanionJob}
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
          <div className="account-portal">
            {account ? <>
              {account.role === "admin" && <a href="#admin">管理后台</a>}
              {account.role !== "admin" && session?.setup_required && <button type="button" onClick={() => setAuthMode("setup")}>配置管理员</button>}
              <button type="button" onClick={() => void logout()} title={account.username} aria-label="退出登录">退出</button>
            </> : <>
              <button type="button" onClick={() => setAuthMode("login")}>登录</button>
              <button type="button" onClick={() => setAuthMode("register")}>注册</button>
            </>}
          </div>
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
              <VerificationLens />
              <div className="hero-shade" />
              <ParticleField motion={effectiveMotion} />
              <div className="hero-content">
                <p className="eyebrow">
                  <span className="live-dot" /> AI 内容核验
                </p>
                <h1>
                  看见线索，
                  <br />
                  核对<span>来源。</span>
                </h1>
                <p className="hero-description">
                  查看图片、语音和视频中的合成线索，核对聊天截图里的说法，了解下一步怎么核实。
                </p>
                <div className="hero-actions">
                  <button
                    className="primary hero-cta"
                    onClick={() => go("check")}
                  >
                    核验材料 <Icon name="arrow" />
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
                  带着线索，回到原始材料和可信来源。
                </p>
              </div>
              <div className="portals">
                {nav.map(([id, label, icon, title, description]) => (
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
                        {label}
                      </span>
                      <Icon name="up" />
                    </div>
                    <div className="portal-art">
                      <Icon name={icon} />
                      <i />
                      <i />
                    </div>
                    <h3>{title}</h3>
                    <p>{description}</p>
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
                  ["02", "查看依据", "对照原话、检测分项和相关资料。"],
                  ["03", "复核来源", "按场景核对原件、原始记录或官方渠道。"],
                ].map(([n, h, p]) => (
                  <div key={n}>
                    <span>{n}</span>
                    <h3>{h}</h3>
                    <p>{p}</p>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
        <div className="workspace" hidden={page === "home"}>
          <div className="workspace-bar">
            <button className="text-button" onClick={() => go("home")}>
              ← 返回首页
            </button>
            <span>{pageTitle(page)}</span>
            <button className="text-button" onClick={() => setModal("help")}>
              使用帮助 <Icon name="help" />
            </button>
          </div>
          <div ref={heading} tabIndex={-1} className="page-focus" />
          {page !== "home" && page !== "report" && (
            <MissionStage page={page} motion={effectiveMotion} />
          )}
          {!account && (page === "check" || page === "history" || page === "report" || page === "contacts") && signIn}
          {account && companionJob && (
            <div hidden={page !== "check"} className="page-enter">
              <CompanionProgress
                key={companionJob.id}
                job={companionJob}
                onComplete={finishCompanionJob}
                onDismiss={() => trackCompanionJob(null)}
              />
            </div>
          )}
          {account && (checkVisited || page === "check") && (
            <div hidden={page !== "check" || !!companionJob} className="page-enter">
              <Boundary>
                <Suspense
                  fallback={
                    <p className="skeleton" role="status">
                      正在打开核验工作台…
                    </p>
                  }
                >
                  <Upload onComplete={finishUpload} />
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
                account ? <Contacts key={account.id} accountId={account.id} isAdmin={account.role === "admin"} /> : null
              ) : page === "practice" ? (
                <Practice />
              ) : !account ? null : page === "history" ? (
                <History onOpen={open} />
              ) : report ? (
                <>
                  {report.id === companionAdviceId && (
                    <CompanionReportAdvice key={"advice-" + report.id} reportId={report.id} />
                  )}
                  <ReportView
                    key={report.id}
                    report={report}
                    previewFile={reportPreviews[report.id]}
                    bundle={bundle}
                    onSelect={setReport}
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
      {authError && !authMode && page === "home" && <p className="auth-global-error error" role="alert">{authError}</p>}
      {auth}
      {completedNotice && (
        <div className="completion-toast" role="status">
          <span>{completedNotice.all.length || 1}份材料已核验完成</span>
          <button
            onClick={() => {
              open(completedNotice.report, completedNotice.all);
              setCompletedNotice(null);
            }}
          >
            查看报告详情 →
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
          <p>AI 内容核验与复核建议</p>
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
        <small>检测结果提供线索，结合原始材料和来源继续核实。</small>
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
                保存在部署电脑。你可在账号内查看或删除报告，部署管理员可为管理需要查阅。删除报告会清除对应反馈和核实记录。
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
                    "选择要核验的材料",
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
                    "按场景核对原始文件、原始记录或相关机构的官方渠道。",
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
