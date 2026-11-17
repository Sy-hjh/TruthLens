import { useEffect, useState } from "react";
import { Icon } from "./ui";
const modes = [
  {
    icon: "audio",
    name: "声音",
    tag: "ACOUSTIC",
    text: "直接检查声学合成特征，再独立提取文字，查看可疑要求。",
  },
  {
    icon: "video",
    name: "视频",
    tag: "TEMPORAL",
    text: "按有序片段检查画面，同时检查音轨和说话内容，分项展示结果。",
  },
  {
    icon: "image",
    name: "照片",
    tag: "VISUAL",
    text: "寻找生成或修改线索。模型输出用于辅助核实，不能确认照片里的人是谁。",
  },
  {
    icon: "chat",
    name: "聊天",
    tag: "CONTEXT",
    text: "提取截图原话，标出值得复核的说法或要求，方便对照原会话。",
  },
];
const checkHints: Record<string, { title: string; text: string }> = {
  audio: {
    title: "怀疑声音被仿造？",
    text: "上传一段语音或通话录音，看看有没有 AI 仿声的线索。",
  },
  video: {
    title: "视频里的人或声音有点不对劲？",
    text: "上传原视频，分别查看画面和声音有没有合成线索。",
  },
  image: {
    title: "怀疑照片被生成或改过？",
    text: "上传原图，看看有没有生成或修改的线索。",
  },
  chat: {
    title: "有人在聊天里提出可疑要求？",
    text: "上传聊天截图，看看哪些话值得再核实。",
  },
};
const pageModes: Record<string, typeof modes> = {
  contacts: [
    {
      icon: "heart",
      name: "保存",
      tag: "TRUST",
      text: "保存事先和家人核对过的常用号码，而不是可疑消息新发来的号码。",
    },
    {
      icon: "phone",
      name: "回拨",
      tag: "CONNECT",
      text: "在下面的联系人卡片发起回拨；手机会交由电话应用确认呼叫。",
    },
    {
      icon: "shield",
      name: "隐私",
      tag: "PRIVATE",
      text: "联系人保存在当前浏览器，不会提供给检测模型或小鉴。",
    },
    {
      icon: "chat",
      name: "核实",
      tag: "VERIFY",
      text: "另找一条可信通路确认要求，熟悉的声音和面孔也不能代替身份核实。",
    },
  ],
  practice: [
    {
      icon: "book",
      name: "教学",
      tag: "EDUCATION",
      text: "作业图片先找原图，论文先核对引用、草稿和创作过程。",
    },
    {
      icon: "image",
      name: "电商",
      tag: "COMMERCE",
      text: "核对售后凭证时，先回到原订单和最早上传的材料。",
    },
    {
      icon: "video",
      name: "新闻",
      tag: "MEDIA",
      text: "核对转发素材时，先找最早的版本、发布时间和原始出处。",
    },
    {
      icon: "shield",
      name: "企业",
      tag: "BUSINESS",
      text: "核对企业文件时，回到原合同、供应商档案和已有审批记录。",
    },
  ],
  history: [
    {
      icon: "lens",
      name: "搜索",
      tag: "FIND",
      text: "在下方按文件名称搜索已有记录，快速找到要复核的材料。",
    },
    {
      icon: "history",
      name: "回看",
      tag: "REVIEW",
      text: "打开报告，分别查看画面、声音和原话中的线索。",
    },
    {
      icon: "upload",
      name: "导出",
      tag: "EXPORT",
      text: "进入报告后可下载检测记录或打印，分享前请检查是否包含私人信息。",
    },
    {
      icon: "shield",
      name: "删除",
      tag: "CONTROL",
      text: "删除报告前会请你确认；确认后同时清除对应反馈与核实步骤。",
    },
  ],
};
const pages: Record<
  string,
  { code: string; title: string; description: string }
> = {
  home: {
    code: "EXPLORE THE SIGNAL",
    title: "四种材料，一个核实起点。",
    description: "点选四个信号，看看真鉴分别检查什么。",
  },
  check: {
    code: "VERIFICATION DECK",
    title: "让每一条线索，都有来处。",
    description: "选择材料后，真实检查进度和结果将在下方展示。",
  },
  contacts: {
    code: "TRUSTED CONNECTION",
    title: "熟悉的声音，还需要可信的联系。",
    description: "这里保存你事先确认的号码，给信任留一条独立通路。",
  },
  practice: {
    code: "VERIFICATION CASES",
    title: "不同场景，核实方法各有侧重。",
    description: "从作业、售后凭证、新闻素材和企业文件里，看看各自应该先核对什么。",
  },
  history: {
    code: "EVIDENCE ARCHIVE",
    title: "每次核实，留下清楚的依据。",
    description: "回看检测分项与原话，和可信的人一起确认。",
  },
  report: {
    code: "SIGNAL OBSERVATORY",
    title: "看见信号，也看懂它的边界。",
    description: "下方才是本次真实检测结果；分项查看，独立核实。",
  },
};
export default function MissionStage({
  page,
  motion,
}: {
  page: string;
  motion: boolean;
}) {
  const [selected, setSelected] = useState(1);
  useEffect(() => {
    setSelected(page === "contacts" || page === "practice" ? 0 : 1);
  }, [page]);
  const currentModes = pageModes[page] || modes;
  const p = pages[page] || pages.home,
    m = currentModes[selected];
  const hint = page === "check" ? checkHints[m.icon] : undefined;
  return (
    <section
      className={
        "mission-stage mission-" +
        page +
        (!motion ? " is-static" : "")
      }
      aria-label="页面交互导览"
    >
      <div className="mission-grid" aria-hidden="true" />
      <div className="mission-nebula" aria-hidden="true" />
      <div className="mission-copy">
        <p className="eyebrow">
          <span className="live-dot" /> {p.code}
        </p>
        <h2>
          {p.title.split("，")[0]}，<br />
          {p.title.split("，")[1]}
        </h2>
        <p>{p.description}</p>
        <button
          className="primary mission-jump"
          onClick={() => {
            if (page === "home") {
              location.hash = "check";
              return;
            }
            const target = document.querySelector<HTMLElement>(".workspace h1");
            if (target) {
              target.scrollIntoView({
                behavior: motion ? "smooth" : "auto",
                block: "start",
              });
              target.tabIndex = -1;
              target.focus({ preventScroll: true });
            }
          }}
        >
          {
            (
              {
                home: "开始核验",
                check: "选择材料",
                contacts: "查看联系人",
                practice: "查看案例",
                history: "查看记录",
                report: "查看本次结果",
              } as Record<string, string>
            )[page]
          }{" "}
          <Icon name="arrow" />
        </button>
        <button
          className="mission-ask"
          onClick={() => dispatchEvent(new Event("truthlens:companion"))}
        >
          让小鉴带我了解 <Icon name="arrow" />
        </button>
        <div className="mission-selection" aria-live="polite">
          {!hint && <span>
            0{selected + 1} / {m.tag}
          </span>}
          <h3>{hint?.title ?? `${m.name}${pageModes[page] ? "小提示" : "怎么检查？"}`}</h3>
          <p>{hint?.text ?? m.text}</p>
        </div>
      </div>
      <div className="mission-system">
        <div className="mission-universe">
          <div className="mission-orbit orbit-one" aria-hidden="true" />
          <div className="mission-orbit orbit-two" aria-hidden="true" />
          <div className="mission-orbit orbit-three" aria-hidden="true" />
          <svg
            className="mission-paths"
            viewBox="0 0 500 400"
            aria-hidden="true"
          >
            <path d="M250 200 100 80M250 200 420 100M250 200 410 320M250 200 80 300" />
            <circle cx="250" cy="200" r="150" />
            <circle cx="250" cy="200" r="115" />
          </svg>
          <div className="mission-core" key={selected}>
            <div className="core-shell" />
            <div className="core-icon">
              <Icon name={m.icon} />
              <span>{m.tag}</span>
            </div>
            <div className="core-sweep" />
          </div>
          {currentModes.map((item, i) => (
            <button
              className={
                "signal-node node-" + i + (selected === i ? " is-active" : "")
              }
              aria-pressed={selected === i}
              key={item.name}
              onClick={() => setSelected(i)}
            >
              <Icon name={item.icon} />
              <span>{item.name}</span>
              <i />
            </button>
          ))}
          <span className="mission-coordinate" aria-hidden="true">
            TRUTHLENS / SIGNAL ATLAS
          </span>
        </div>
      </div>
    </section>
  );
}
