import { useState } from "react";
import type { FormEvent } from "react";
import { api, jsonRequest } from "./api";
import type { Account } from "./api";
import { Dialog, Icon, errorText } from "./ui";
import "./admin.css";

export type AccessMode = "login" | "register" | "setup";
const titles = { login: "登录真鉴", register: "创建账号", setup: "初始化管理员" };

export function AccountAccess({ initialMode, setupRequired, close, onSuccess }: {
  initialMode: AccessMode;
  setupRequired: boolean;
  close: () => void;
  onSuccess: (account: Account) => void;
}) {
  const [mode, setMode] = useState(initialMode);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  function switchMode(next: AccessMode) { setMode(next); setError(""); }
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    const username = String(fields.get("username")).trim();
    const password = String(fields.get("password"));
    setError("");
    if (mode !== "login" && password !== fields.get("confirm")) {
      setError("两次输入的密码不一致。");
      return;
    }
    setBusy(true);
    try {
      const result = await api<{ account: Account }>("/api/auth/" + mode, jsonRequest("POST", {
        username, password, ...(mode === "setup" ? { token: String(fields.get("token")).trim() } : {}),
      }));
      onSuccess(result.account);
    } catch (error) { setError(errorText(error)); }
    finally { setBusy(false); }
  }
  return (
    <Dialog title={titles[mode]} onClose={close} className="access-dialog">
      <p className="access-intro">{mode === "setup" ? "使用部署电脑上的一次性初始化码创建首位管理员。"
        : "登录后可提交核验材料并查看你的报告。"}</p>
      {mode !== "setup" && (
        <div className="access-switch" aria-label="登录或注册">
          <button type="button" aria-pressed={mode === "login"} onClick={() => switchMode("login")} disabled={busy}>登录</button>
          <button type="button" aria-pressed={mode === "register"} onClick={() => switchMode("register")} disabled={busy}>注册</button>
        </div>
      )}
      <form className="access-form" onSubmit={submit} key={mode}>
        <label>用户名<input name="username" autoComplete="username" minLength={2} maxLength={32} required /></label>
        <label>密码<input name="password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={8} maxLength={128} required /></label>
        {mode !== "login" && <label>确认密码<input name="confirm" type="password" autoComplete="new-password" minLength={8} maxLength={128} required /></label>}
        {mode === "setup" && <label>一次性初始化码<input name="token" type="password" autoComplete="off" required /><small>查看部署电脑的 runtime/admin-setup.txt。</small></label>}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" disabled={busy}>{busy ? "正在提交…" : titles[mode]} <Icon name="arrow" /></button>
      </form>
      {setupRequired && mode !== "setup" && (
        <button className="text-button access-setup" onClick={() => switchMode("setup")} disabled={busy}>首次配置管理员</button>
      )}
      {mode === "setup" && <button className="text-button access-setup" onClick={() => switchMode("login")} disabled={busy}>返回登录</button>}
    </Dialog>
  );
}
