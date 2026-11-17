import { Dialog } from "../ui";
import { useEffect, useState } from "react";
import type { FormEvent } from "react";
interface Contact {
  name: string;
  phone: string;
}
const legacyKey = "qinan-contacts";
function read(key: string, includeLegacy: boolean): Contact[] {
  try {
    const d: unknown = JSON.parse(localStorage.getItem(key) || (includeLegacy ? localStorage.getItem(legacyKey) : null) || "[]");
    return Array.isArray(d)
      ? d.filter(
          (x): x is Contact =>
            typeof x?.name === "string" &&
            typeof x?.phone === "string" &&
            /^\+?[\d -]{5,25}$/.test(x.phone),
        )
      : [];
  } catch {
    return [];
  }
}
export default function Contacts({ accountId, isAdmin }: { accountId: number; isAdmin: boolean }) {
  const key = legacyKey + "-" + accountId;
  const [pending, setPending] = useState<number | null>(null);
  const [rows, setRows] = useState<Contact[]>(() => read(key, isAdmin)),
    [name, setName] = useState(""),
    [phone, setPhone] = useState(""),
    [message, setMessage] = useState("");
  function save(next: Contact[]) {
    try {
      localStorage.setItem(key, JSON.stringify(next));
      setRows(next);
      return true;
    } catch {
      setMessage("浏览器未允许保存，请检查隐私设置或记录在纸上。");
      return false;
    }
  }
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!/^\+?[\d -]{5,25}$/.test(phone.trim())) {
      setMessage("请检查电话号码，只填写号码、空格和短横线。");
      return;
    }
    if (save([...rows, { name: name.trim(), phone: phone.trim() }])) {
      setName("");
      setPhone("");
      setMessage("已经保存在这台设备的浏览器中。");
    }
  }
  useEffect(() => {
    setMessage("");
  }, []);
  return (
    <>
      <p className="eyebrow">提前保存 · 独立回拨</p>
      <h1>联系我的家人</h1>
      <p className="page-intro">
        请和家人当面确认号码后保存。不要填写可疑消息刚提供的号码。
      </p>
      <div className="check-grid">
        <section>
          <div className="contact-list">
            {rows.length ? (
              rows.map((c, i) => (
                <article className="card contact" key={i}>
                  <span className="avatar">{c.name.slice(0, 1)}</span>
                  <div>
                    <h2>{c.name}</h2>
                    <p>{c.phone}</p>
                  </div>
                  <a
                    className="primary"
                    href={"tel:" + c.phone.replace(/[^+\d]/g, "")}
                  >
                    拨打电话 ↗
                  </a>
                  <button className="quiet" onClick={() => setPending(i)}>
                    移除
                  </button>
                </article>
              ))
            ) : (
              <article className="empty card">
                <span>♡</span>
                <h2>先保存一位信任的家人</h2>
                <p>遇到可疑视频时，就能从这里找到原先确认的号码。</p>
              </article>
            )}
          </div>
          <div className="notice soft">
            <h3>手机打开，也能使用</h3>
            <p>
              点击“拨打电话”会交给设备拨号程序，由您确认。电脑需要已配置电话程序；TruthLens真鉴不会自动拨号。
            </p>
          </div>
        </section>
        <form className="card" onSubmit={submit}>
          <h2>添加家人号码</h2>
          <label className="field">
            家人称呼
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              maxLength={30}
              placeholder="例如：女儿小林"
            />
          </label>
          <label className="field">
            事先确认的电话号码
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              required
              type="tel"
              maxLength={25}
              placeholder="填写家人的常用号码"
            />
          </label>
          <button className="primary wide">保存家人号码</button>
          <p className="muted">
            号码只存于当前浏览器，不发送给模型或其他服务。换设备需重新保存。
          </p>
          <p role="status">{message}</p>
        </form>
      </div>
      {pending !== null && (
        <Dialog title="移除这个号码？" onClose={() => setPending(null)}>
          <p>
            将从当前浏览器移除 {rows[pending]?.name}{" "}
            的联系方式，之后可以重新添加。
          </p>
          <div className="toolbar">
            <button onClick={() => setPending(null)}>保留号码</button>
            <button
              className="primary"
              onClick={() => {
                if (save(rows.filter((_, i) => i !== pending)))
                  setPending(null);
              }}
            >
              确认移除
            </button>
          </div>
        </Dialog>
      )}
    </>
  );
}
