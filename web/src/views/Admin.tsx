import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api, jsonRequest } from "../api";
import type { Account, CaseEntry } from "../api";
import { caseCategories } from "../quiz-data";
import { Dialog, Icon, errorText } from "../ui";

type Tab = "models" | "catalog" | "accounts" | "data";
type Catalog = "cases" | "knowledge";
type Knowledge = { id: string; title: string; snippet: string; url: string; date: string;
  workflow: boolean; action: "source" | "callback" | "protect" | "pause" | "account"; status: CaseEntry["status"] };
type Activity = { id: number; actor: string; operation: string; target: string; created_at: string };
type Dashboard = { accounts: number; active_accounts: number; reports: number; logs: Activity[];
  detectors: { name: string; version: string; available: boolean }[] };
type Rules = Record<"whole_threshold" | "fused_threshold" | "fused_photo_threshold" | "daf_signal_threshold"
  | "daf_box_threshold" | "whole_weight" | "fused_weight" | "daf_weight" | "retention_days", number>;
type Release = { version: number; values: Rules; actor: string; created_at: string };
type Releases = { current: Release; versions: Release[] };

const tabs = [
  ["models", "settings", "模型与阈值", "查看运行状态，配置图片核验与画框规则。"],
  ["catalog", "book", "案例与知识库", "发布核验案例，更新小鉴检索的资料。"],
  ["accounts", "shield", "账号与权限", "查看成员，管理账号状态和访问权限。"],
  ["data", "history", "数据与操作日志", "配置报告保留期限，查看管理和报告操作记录。"],
] as const;
const ruleFields: { key: keyof Rules; label: string; hint: string; weight?: boolean }[] = [
  { key: "whole_threshold", label: "整图合成提醒", hint: "整图分达到此值后，报告提示存在合成线索。" },
  { key: "fused_threshold", label: "FUSED 文档区域", hint: "用于在任务相关字段内定位可疑像素。" },
  { key: "fused_photo_threshold", label: "FUSED 无文字图片", hint: "用于有集中异常响应的普通照片。" },
  { key: "daf_signal_threshold", label: "DAF 候选线索", hint: "筛选可能存在编辑痕迹的文字候选框。" },
  { key: "daf_box_threshold", label: "DAF 黄框", hint: "关键字段分数达线时，根据报告规则标出单模型线索。" },
  { key: "whole_weight", label: "整图权重", hint: "%", weight: true },
  { key: "fused_weight", label: "FUSED 权重", hint: "%", weight: true },
  { key: "daf_weight", label: "DAF 权重", hint: "%", weight: true },
];
const formatDate = (stamp: string) => new Intl.DateTimeFormat("zh-CN", {
  dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Shanghai",
}).format(new Date(stamp));
const stateLabel = { draft: "草稿", published: "已发布", archived: "已下架" };

export default function Admin({ account, onLogout }: { account: Account; onLogout: () => void }) {
  const [tab, setTab] = useState<Tab>("models");
  const [kind, setKind] = useState<Catalog>("cases");
  const [settings, setSettings] = useState<Releases | null>(null);
  const [rules, setRules] = useState<Rules | null>(null);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [items, setItems] = useState<CaseEntry[]>([]);
  const [knowledge, setKnowledge] = useState<Knowledge[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [query, setQuery] = useState("");
  const [logQuery, setLogQuery] = useState("");
  const [selection, setSelection] = useState<CaseEntry | Knowledge | "new" | null>(null);
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [confirm, setConfirm] = useState<{ text: string; action: () => void } | null>(null);

  async function refresh() {
    const [nextSettings, nextDashboard, nextItems, nextKnowledge] = await Promise.all([
      api<Releases>("/api/admin/settings"), api<Dashboard>("/api/admin/data"),
      api<CaseEntry[]>("/api/admin/catalog/cases"), api<Knowledge[]>("/api/admin/catalog/knowledge"),
    ]);
    setSettings(nextSettings);
    setRules(nextSettings.current.values);
    setDashboard(nextDashboard);
    setItems(nextItems);
    setKnowledge(nextKnowledge);
    setReady(true);
  }
  useEffect(() => {
    void refresh().catch((error) => setError(errorText(error)));
  }, []);
  useEffect(() => {
    if (tab !== "accounts") return;
    let active = true;
    const timer = window.setTimeout(() => {
      void api<Account[]>("/api/admin/accounts?q=" + encodeURIComponent(query.trim())).then((rows) => {
        if (active) setAccounts(rows);
      }).catch((error) => { if (active) setError(errorText(error)); });
    }, 170);
    return () => { active = false; clearTimeout(timer); };
  }, [tab, query]);

  async function mutate(action: () => Promise<unknown>, success: string) {
    setError(""); setNotice(""); setBusy(true);
    try {
      await action();
      setNotice(success);
      await refresh();
      if (tab === "accounts") setAccounts(await api<Account[]>("/api/admin/accounts?q=" + encodeURIComponent(query.trim())));
      return true;
    } catch (error) {
      setError(errorText(error));
      return false;
    } finally { setBusy(false); }
  }

  function updateAccount(person: Account, role: Account["role"], active: boolean) {
    const action = () => void mutate(
      () => api("/api/admin/accounts/" + person.id, jsonRequest("PATCH", { role, active })), "账号已更新。",
    );
    setConfirm({ text: `将「${person.username}」设为${active ? "启用" : "停用"}的${role === "admin" ? "管理员" : "普通用户"}？`, action });
  }

  function saveCatalog(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const read = (field: string) => String(form.get(field) ?? "").trim();
    const item = selection === "new" ? null : selection;
    const existing = item && "source" in item ? item.source : null;
    const url = read("url"), title = read("title"), status = read("status"), date = read("date");
    const body = kind === "cases" ? {
      title, status, category: read("category"), kind: read("kind"), scenario: read("scenario"), next: read("next"),
      source: { date, url, publisher: read("publisher"), label: existing?.label, related: existing?.related },
    } : { title, status, date, url, snippet: read("snippet"), action: read("action"), workflow: form.has("workflow") };
    void mutate(() => api("/api/admin/catalog/" + kind + "/" + (item?.id ?? "new"), jsonRequest("PUT", body)),
      status === "published" ? "已发布，用户端现在可以使用。" : status === "archived" ? "已下架。" : "草稿已保存。")
      .then((ok) => { if (ok) setSelection(null); });
  }

  const current = tabs.find(([id]) => id === tab)!;
  const list = kind === "cases" ? items : knowledge;
  const editCase = selection && selection !== "new" && "source" in selection ? selection : null;
  const editKnowledge = selection && selection !== "new" && "snippet" in selection ? selection : null;
  const totalWeight = rules ? rules.whole_weight + rules.fused_weight + rules.daf_weight : 0;
  const filteredLogs = (dashboard?.logs ?? []).filter((item) =>
    [item.actor, item.operation, item.target].some((s) => s.toLowerCase().includes(logQuery.trim().toLowerCase())));

  return (
    <div className="admin-shell">
      <aside className="admin-rail">
        <a className="admin-brand" href="#home"><span><Icon name="lens" /></span><div><b>TruthLens</b><small>真鉴管理后台</small></div></a>
        <nav aria-label="管理后台">
          {tabs.map(([key, icon, title]) => <button type="button" key={key} aria-current={tab === key ? "page" : undefined}
            onClick={() => { setTab(key); setError(""); setNotice(""); }}><Icon name={icon} />{title}<span aria-hidden="true">›</span></button>)}
        </nav>
        <div className="admin-rail-bottom"><a href="#home">← 返回用户端</a><button type="button" onClick={onLogout}>退出登录</button></div>
      </aside>
      <main className="admin-workspace" id="main-content">
        <header className="admin-title">
          <div><div className="admin-breadcrumb">管理后台 <span>/</span> {current[2]}</div><h1>{current[2]}</h1><p>{current[3]}</p></div>
          <div className="admin-profile"><span>{Array.from(account.username)[0]}</span><div><b>{account.username}</b><small>管理员</small></div></div>
        </header>
        {error && !selection && <p className="admin-message error" role="alert">{error}</p>}
        {notice && <p className="admin-message" role="status">{notice}</p>}
        {!ready && <button className="text-button" disabled={!error} onClick={() => void refresh().catch((error) => setError(errorText(error)))}>
          {error ? "重试加载" : "正在加载…"}
        </button>}

        {tab === "models" && settings && rules && dashboard && (
          <>
            <section className="admin-overview">
              {dashboard.detectors.map((detector) => <article key={detector.name}><span className={detector.available ? "admin-state on" : "admin-state"}>{detector.available ? "可用" : "不可用"}</span>
                <h2>{detector.name}</h2><p>{detector.version}</p></article>)}
            </section>
            <div className="admin-columns">
              <section className="admin-panel">
                <div className="admin-section-head"><div><h2>图片检测规则</h2><p>配置发布后用于新任务。红框仍要求 FUSED 与 DAF 在同一字段重合。</p></div>
                  <span className="admin-state on">当前 v{settings.current.version}</span></div>
                <form onSubmit={(event) => {
                  event.preventDefault();
                  void mutate(() => api("/api/admin/settings", jsonRequest("PUT", { ...rules, base_version: settings.current.version })),
                    "检测配置已发布。");
                }}>
                  {[false, true].map((weights) => (
                    <div className={weights ? "admin-rule-grid admin-weight-grid" : "admin-rule-grid"} key={String(weights)}>
                      {ruleFields.filter((field) => Boolean(field.weight) === weights).map((field) => <label key={field.key}>{field.label}
                        <input type="number" min={weights ? 0 : 0.01} max={weights ? 100 : 1} step={weights ? 1 : 0.01} required
                          value={Number.isFinite(rules[field.key]) ? rules[field.key] : ""} onChange={(event) => setRules({ ...rules, [field.key]: event.currentTarget.valueAsNumber })} />
                        {!weights && <small>{field.hint}</small>}</label>)}
                    </div>
                  ))}
                  <div className="admin-form-actions"><small>权重合计 {Number.isFinite(totalWeight) ? totalWeight : "—"}%</small>
                    <button className="primary" disabled={busy || totalWeight !== 100}>发布配置 <Icon name="arrow" /></button></div>
                </form>
              </section>
              <section className="admin-panel">
                <div className="admin-section-head"><div><h2>配置历史</h2><p>恢复历史规则会生成一个新版本。</p></div></div>
                <ul className="admin-releases">{settings.versions.map((version) => <li key={version.version}>
                  <div><b>v{version.version}</b><small>{version.actor} · {formatDate(version.created_at)}</small></div>
                  {version.version === settings.current.version ? <span className="admin-state on">当前</span> :
                    <button disabled={busy} onClick={() => setConfirm({ text: `恢复 v${version.version} 的检测配置？`, action: () =>
                      void mutate(() => api(`/api/admin/settings/${version.version}/restore`, { method: "POST" }), "检测配置已恢复。") })}>恢复</button>}
                </li>)}</ul>
              </section>
            </div>
          </>
        )}

        {tab === "catalog" && ready && (
          <section className="admin-panel">
            <div className="admin-section-head">
              <div className="admin-switch" aria-label="内容类型">
                <button aria-pressed={kind === "cases"} onClick={() => setKind("cases")}>核验案例 <span>{items.length}</span></button>
                <button aria-pressed={kind === "knowledge"} onClick={() => setKind("knowledge")}>小鉴知识库 <span>{knowledge.length}</span></button>
              </div>
              <button className="primary" onClick={() => { setError(""); setSelection("new"); }}>新增{kind === "cases" ? "案例" : "知识"} <Icon name="up" /></button>
            </div>
            <div className="admin-table-wrap"><table><thead><tr><th>标题</th><th>{kind === "cases" ? "场景" : "资料用途"}</th><th>发布状态</th><th>操作</th></tr></thead>
              <tbody>{list.map((item) => <tr key={item.id}>
                <th scope="row">{item.title}</th><td>{"category" in item ? item.category : item.workflow ? "流程指导" : "公开资料"}</td>
                <td><span className={item.status === "published" ? "admin-state on" : "admin-state"}>{stateLabel[item.status]}</span></td>
                <td><button onClick={() => { setError(""); setSelection(item); }}>编辑</button></td>
              </tr>)}</tbody></table></div>
            {list.length === 0 && <p className="admin-empty">暂无条目。</p>}
          </section>
        )}
        {tab === "accounts" && ready && (
          <section className="admin-panel">
            <div className="admin-section-head"><div><h2>账号列表</h2><p>共 {dashboard?.accounts ?? 0} 个账号 · {dashboard?.active_accounts ?? 0} 个启用</p></div>
              <input className="admin-search" aria-label="搜索用户名" placeholder="搜索用户名" maxLength={32} value={query} onChange={(event) => setQuery(event.target.value)} /></div>
            <div className="admin-table-wrap"><table><thead><tr><th>用户名</th><th>角色</th><th>状态</th><th>注册时间</th><th>操作</th></tr></thead>
              <tbody>{accounts.map((person) => <tr key={person.id}><th scope="row">{person.username}{person.id === account.id && <small>（我）</small>}</th>
                <td><select aria-label={person.username + "的角色"} value={person.role} disabled={person.id === account.id || busy}
                  onChange={(event) => updateAccount(person, event.target.value as Account["role"], person.active)}><option value="user">普通用户</option><option value="admin">管理员</option></select></td>
                <td><span className={person.active ? "admin-state on" : "admin-state"}>{person.active ? "启用" : "停用"}</span></td>
                <td>{formatDate(person.created_at)}</td><td><button disabled={person.id === account.id || busy}
                  onClick={() => updateAccount(person, person.role, !person.active)}>{person.active ? "停用" : "启用"}</button></td></tr>)}</tbody></table></div>
            {accounts.length === 0 && <p className="admin-empty">没有匹配的账号。</p>}
          </section>
        )}
        {tab === "data" && dashboard && settings && rules && (
          <>
            <section className="admin-overview admin-overview-data">
              <article><span>核验报告</span><h2>{dashboard.reports}</h2><p>数据库中现存的报告</p></article>
              <article><span>报告保留期限</span><h2>{settings.current.values.retention_days ? settings.current.values.retention_days + " 天" : "长期保留"}</h2><p>上传副本在核验结束后清理</p></article>
              <article><span>可查操作记录</span><h2>{dashboard.logs.length}</h2><p>显示最近 150 条记录</p></article>
            </section>
            <div className="admin-data-grid">
              <section className="admin-panel">
                <div className="admin-section-head"><div><h2>报告保留设置</h2><p>0 天表示长期保留。设置保留期后，服务会定期清理超期报告，包括已有报告。</p></div></div>
                <form className="admin-inline-form" onSubmit={(event) => {
                  event.preventDefault();
                  const action = () => void mutate(() => api("/api/admin/retention", jsonRequest("PUT", {
                    retention_days: rules.retention_days, base_version: settings.current.version,
                  })), "报告保留期限已更新。");
                  if (rules.retention_days > 0) setConfirm({ text: `启用 ${rules.retention_days} 天保留期？超期报告会在定期清理时删除。`, action });
                  else action();
                }}>
                  <label>保留天数<input type="number" min="0" max="3650" step="1" required
                    value={Number.isFinite(rules.retention_days) ? rules.retention_days : ""}
                    onChange={(event) => setRules({ ...rules, retention_days: event.currentTarget.valueAsNumber })} /></label>
                  <button className="primary" disabled={busy}>保存保留期限</button>
                  <a href="#history">查看核验记录 ↗</a>
                </form>
              </section>
              <section className="admin-panel">
                <div className="admin-section-head"><div><h2>操作日志</h2><p>按时间倒序查看账号、内容与报告操作。</p></div>
                  <input className="admin-search" aria-label="搜索日志" placeholder="搜索操作或账号" value={logQuery} onChange={(event) => setLogQuery(event.target.value)} /></div>
                <div className="admin-table-wrap"><table><thead><tr><th>时间</th><th>账号</th><th>操作</th><th>对象</th></tr></thead>
                  <tbody>{filteredLogs.map((entry) => <tr key={entry.id}><td>{formatDate(entry.created_at)}</td><td>{entry.actor}</td>
                    <th scope="row">{entry.operation}</th><td className="admin-log-target">{entry.target || "—"}</td></tr>)}</tbody></table></div>
                {filteredLogs.length === 0 && <p className="admin-empty">没有匹配的日志。</p>}
              </section>
            </div>
          </>
        )}
      </main>
      {selection && (
        <Dialog title={(selection === "new" ? "新增" : "编辑") + (kind === "cases" ? "核验案例" : "知识条目")}
          onClose={() => { if (!busy) setSelection(null); }} className="admin-editor">
          <form className="admin-editor-form" onSubmit={saveCatalog}>
            <label>标题<input name="title" defaultValue={editCase?.title ?? editKnowledge?.title} minLength={2} maxLength={120} required /></label>
            {kind === "cases" ? (
              <>
                <div className="admin-editor-row"><label>场景<select name="category" defaultValue={editCase?.category}>{caseCategories.slice(1).map((value) => <option key={value}>{value}</option>)}</select></label>
                  <label>类型<select name="kind" defaultValue={editCase?.kind}><option>真实案例</option><option>实地研究</option></select></label></div>
                <label>案例内容<textarea name="scenario" defaultValue={editCase?.scenario} maxLength={1800} required /></label>
                <label>核实建议<textarea name="next" defaultValue={editCase?.next} maxLength={1800} required /></label>
                <label>发布机构<input name="publisher" defaultValue={editCase?.source.publisher} maxLength={100} required /></label>
              </>
            ) : (
              <>
                <label>资料摘要<textarea name="snippet" defaultValue={editKnowledge?.snippet} maxLength={1800} required /></label>
                <label>核实动作<select name="action" defaultValue={editKnowledge?.action ?? "source"}><option value="source">核对来源</option>
                  <option value="callback">联系本人</option><option value="protect">保护个人信息</option><option value="pause">暂停操作</option><option value="account">核对账号</option></select></label>
                <label className="admin-checkbox"><input type="checkbox" name="workflow" defaultChecked={editKnowledge?.workflow} />作为流程指导资料</label>
              </>
            )}
            <label>来源网址<input name="url" type="url" defaultValue={editCase?.source.url ?? editKnowledge?.url} maxLength={1000} placeholder="https://" required /></label>
            <div className="admin-editor-row"><label>发布日期<input name="date" defaultValue={editCase?.source.date ?? editKnowledge?.date} maxLength={30} placeholder="YYYY-MM-DD" /></label>
              <label>发布状态<select name="status" defaultValue={selection === "new" ? "draft" : selection.status}>
                <option value="draft">草稿</option><option value="published">发布到用户端</option><option value="archived">下架</option></select></label></div>
            {error && <p className="error" role="alert">{error}</p>}
            <button className="primary" disabled={busy}>{busy ? "正在保存…" : "保存条目"} <Icon name="arrow" /></button>
          </form>
        </Dialog>
      )}
      {confirm && <Dialog title="确认变更" onClose={() => setConfirm(null)} className="admin-editor">
        <p>{confirm.text}</p><div className="admin-form-actions"><button onClick={() => setConfirm(null)}>取消</button>
          <button className="primary" onClick={() => { confirm.action(); setConfirm(null); }}>确认</button></div>
      </Dialog>}
    </div>
  );
}
