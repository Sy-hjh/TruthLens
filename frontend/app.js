const $ = (id) => document.getElementById(id);
const esc = (x) =>
  String(x ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let previewURL, report, productReady = false;
async function api(path, options) {
  let response;
  try {
    response = await fetch(path, options);
  } catch {
    throw Error("连接中断。请确认亲安服务正在运行，再刷新页面。");
  }
  const data = await response.json();
  if (!response.ok)
    throw Error(typeof data.detail === "string" ? data.detail : "请求失败");
  return data;
}
function show(id) {
  ["check", "contacts", "practice", "history", "result"].forEach(
    (x) => ($(x).hidden = x !== id),
  );
  document
    .querySelectorAll(".nav")
    .forEach((b) => b.classList.toggle("active", b.dataset.page === id));
  if (id === "contacts") contacts();
  if (id === "history") history();
  if (id === "practice") quiz();
  window.scrollTo(0, 0);
}
document
  .querySelectorAll("[data-page]")
  .forEach((b) => (b.onclick = () => show(b.dataset.page)));
api("/api/health")
  .then(
    (s) => {
      $("status").textContent = `服务已连接 · 视频${s.models.video ? "就绪" : "未安装"} · 声音${s.models.audio ? "就绪" : "未安装"}`;
      if(s.models.product){productReady=true;$("product-option").disabled=false;$("product-option").textContent="商品改图核验";}
    },
  )
  .catch((e) => ($("status").textContent = e.message));
$("file").onchange = () => {
  const file = $("file").files[0];
  if (!file) return;
  $("filename").textContent = file.name;
  $("preview").replaceChildren();
  if (previewURL) URL.revokeObjectURL(previewURL);
  previewURL = URL.createObjectURL(file);
  const type = file.type.startsWith("video")
    ? "video"
    : file.type.startsWith("audio")
      ? "audio"
      : "img";
  const el = document.createElement(type);
  $("scene-field").hidden=type!=="img" || !productReady;
  if(type!=="img")$("scene").value="general";
  el.src = previewURL;
  if (type !== "img") el.controls = true;
  $("preview").append(el);
};
$("form").onsubmit = async (e) => {
  e.preventDefault();
  $("error").textContent = "";
  if ($("file").files[0].size > 104857600) {
    $("error").textContent = "文件超过100MB";
    return;
  }
  $("submit").disabled = true;
  try {
    const { job_id } = await api("/api/analyze", {
      method: "POST",
      body: new FormData(e.target),
    });
    let failures = 0;
    for (;;) {
      let job;
      try {
        job = await api("/api/jobs/" + job_id);
        failures = 0;
      } catch (err) {
        if (++failures >= 3) throw err;
        await new Promise((r) => setTimeout(r, 2000));
        continue;
      }
      $("progress").textContent = job.message;
      if (job.status === "completed") {
        render(job.result);
        break;
      }
      if (job.status === "failed") throw Error(job.message);
      await new Promise((r) => setTimeout(r, 1500));
    }
  } catch (err) {
    $("error").textContent = err.message;
  } finally {
    $("submit").disabled = false;
  }
};
function speak(text) {
  const name = report?.summary?.includes("局部编辑")
    ? "guidance-edited-image"
    : report?.summary?.includes("整图生成")
      ? "guidance-ai-image"
      : report?.summary?.includes("未取得") ||
          report?.summary?.includes("未成功")
        ? "guidance-inconclusive"
        : "guidance-contact-family";
  let player = $("report-voice");
  if (!player) {
    player = document.createElement("audio");
    player.id = "report-voice";
    player.controls = true;
    player.setAttribute("aria-label", "核验摘要语音提醒");
    $("result").append(player);
  }
  player.src = "/api/demo/" + name;
  player.play().catch(() => alert("请点击下方音频播放器播放核验提醒。"));
}
function render(r) {
  report = r;
  show("result");
  const names = {
    video: "视频画面",
    audio: "声音",
    image: "整图生成线索",
    tamper: "局部编辑线索与定位",
  };
  $("result").innerHTML =
    `<p class="eyebrow">核验报告</p><h1>${esc(r.summary)}</h1><div class="toolbar"><button id="read">听核验摘要</button><button id="print">打印报告</button><button id="export">导出记录</button></div><button class="primary" id="call">联系预留家人，独立核实</button><article class="card">${Object.entries(
      r.modules,
    )
      .map(
        ([key, m]) =>
          `<section class="module"><h2>${names[key] || esc(key)} · ${m.status === "completed" ? "已分析" : "未能完成"}</h2><p>${esc(m.note)}</p>${m.score !== undefined ? `<p>模型原始分数：${(m.score * 100).toFixed(1)} /100（不是诈骗概率）</p>` : ""}${(m.segments || []).map((s) => `<p>${s.start.toFixed(0)}秒起：${esc(s.signal || "模型分数")} · ${(s.score * 100).toFixed(1)} /100</p>`).join("")}${m.map_png ? `<figure class="anomaly"><img src="${esc(m.map_png)}" alt="模型预测异常分布图"><figcaption>亮处为模型预测异常较高的位置；不是已证实的修改区域。</figcaption></figure>` : ""}<small>${esc(m.source?.repo || m.segments?.[0]?.source?.repo || "")}</small></section>`,
      )
      .join(
        "",
      )}${r.transcript ? `<section class="module"><h2>听到了什么</h2><p>${esc(r.transcript.text || "转写未完成")}</p><small>${esc(r.transcript.note)}</small></section>` : ""}<h2>需要核实的表达</h2>${r.phrases.length ? r.phrases.map((p) => `<p>${esc(p.source || "您填写的描述")}：“${esc(p.context || p.excerpt)}”：${esc(p.category)}。${esc(p.note)}</p>`).join("") : "<p>未命中内置规则，不表示安全。</p>"}<div class="notice"><h2>接下来怎么做</h2>${r.next_steps.map((x) => `<p>${esc(x)}</p>`).join("")}</div><details><summary>查看检测范围与技术信息</summary>${r.limitations.map((x) => `<p>${esc(x)}</p>`).join("")}<p class="hash">文件哈希：${esc(r.sha256)}</p><p>处理后原始文件已删除，报告只保留模型结果和您填写的描述。</p></details></article>`;
  $("read").onclick = () => speak(r.summary + "。" + r.next_steps.join("。"));
  $("call").onclick = () => show("contacts");
  $("print").onclick = () => print();
  $("export").onclick = () => {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(r, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "亲安-" + r.id + ".json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };
}
async function history() {
  try {
    const rows = await api("/api/cases");
    $("records").innerHTML = rows.length
      ? rows
          .map(
            (r) =>
              `<article class="record"><div><b>${esc(r.filename)}</b><p>${esc(new Date(r.created_at).toLocaleString())}</p></div><button data-open="${r.id}">查看</button><button data-delete="${r.id}">删除</button></article>`,
          )
          .join("")
      : "还没有记录。";
    $("records")
      .querySelectorAll("[data-open]")
      .forEach(
        (b) =>
          (b.onclick = async () => {
            try {
              render(await api("/api/cases/" + b.dataset.open));
            } catch (e) {
              alert(e.message);
            }
          }),
      );
    $("records")
      .querySelectorAll("[data-delete]")
      .forEach(
        (b) =>
          (b.onclick = async () => {
            if (confirm("删除此报告？")) {
              try {
                await api("/api/cases/" + b.dataset.delete, {
                  method: "DELETE",
                });
                history();
              } catch (e) {
                alert(e.message);
              }
            }
          }),
      );
  } catch (e) {
    $("records").textContent = e.message;
  }
}
function saved() {
  try {
    const data = JSON.parse(localStorage.getItem("qinan-contacts") || "[]");
    return Array.isArray(data)
      ? data.filter(
          (x) =>
            typeof x.name === "string" && /^\+?[\d -]{5,25}$/.test(x.phone),
        )
      : [];
  } catch {
    return [];
  }
}
function contacts() {
  const rows = saved();
  $("contact-list").innerHTML = rows.length
    ? rows
        .map(
          (c, i) =>
            `<article class="record"><div><b>${esc(c.name)}</b><p>${esc(c.phone)}</p></div><a href="tel:${c.phone.replace(/[^+\d]/g, "")}">拨打电话</a><button data-remove="${i}">移除</button></article>`,
        )
        .join("")
    : "请先与家人确认号码，再在上方保存。";
  $("contact-list")
    .querySelectorAll("[data-remove]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          if (confirm("移除此联系人？")) {
            rows.splice(Number(b.dataset.remove), 1);
            localStorage.setItem("qinan-contacts", JSON.stringify(rows));
            contacts();
          }
        }),
    );
}
$("contact-form").onsubmit = (e) => {
  e.preventDefault();
  const phone = $("phone").value.trim();
  if (!/^\+?[\d -]{5,25}$/.test(phone)) {
    alert("请检查电话号码");
    return;
  }
  try {
    const rows = saved();
    rows.push({ name: $("person").value.trim(), phone });
    localStorage.setItem("qinan-contacts", JSON.stringify(rows));
    e.target.reset();
    contacts();
  } catch {
    alert("浏览器未允许保存，请检查设置");
  }
};
const questions = [
  {
    q: "视频里的人很像孙子，说出事了，要马上转钱，还说不要告诉父母。您怎么做？",
    choices: ["马上转钱，视频看着是真的", "暂停转账，用提前保存的常用号码核实"],
    answer: 1,
    why: "面孔和声音也可能被模仿。使用原先确认的号码独立核实，别拨对方临时给的号码。",
  },
  {
    q: "语音听起来很熟悉，检测也没有发现合成信号，就一定安全吗？",
    choices: ["一定安全", "仍需核实，模型可能漏检"],
    answer: 1,
    why: "检测没有发现异常，不代表身份真实或请求合理。",
  },
  {
    q: "视频里的“专家”说，购买某产品能保证治好疾病，并催您付款。",
    choices: ["因为是专家，直接买", "先核实身份、产品与宣传依据"],
    answer: 1,
    why: "外貌像专家也可能是冒用；宣传承诺需要独立核实。",
  },
];
let qi = 0;
function quiz() {
  const q = questions[qi % questions.length];
  $("quiz").innerHTML =
    `<p>第${(qi % questions.length) + 1}题 / ${questions.length} · 情境练习，不是真实来电</p><h2>${q.q}</h2>${q.choices.map((x, i) => `<button class="quiz-option" data-answer="${i}">${x}</button>`).join("")}<p id="feedback" aria-live="polite"></p><button id="next" class="primary" hidden>下一题</button>`;
  $("quiz")
    .querySelectorAll("[data-answer]")
    .forEach(
      (b) =>
        (b.onclick = () => {
          $("feedback").textContent =
            (Number(b.dataset.answer) === q.answer
              ? "这一步做得对。"
              : "先别着急。") + q.why;
          $("next").hidden = false;
        }),
    );
  $("next").onclick = () => {
    qi++;
    quiz();
  };
}
