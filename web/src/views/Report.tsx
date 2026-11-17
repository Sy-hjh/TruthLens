import { focusQuestions } from "../ui";
import AgentReview from "./AgentReview";
import SpeechContent from "./SpeechContent";
import DetectionEvidence from "./DetectionEvidence";
import ChatReport, { ChatTextReview } from "./ChatReport";
import { useEffect, useState } from "react";
import { downloadReport } from "../api";
import type { Report as ReportData } from "../api";
import { moduleSignal } from "../signals";
const names: Record<string, string> = {
  video: "视频画面检查",
  audio: "声学合成检测",
  image: "整图生成",
  tamper: "局部篡改",
};
type Props = {
  report: ReportData;
  onUpdate: (r: ReportData) => void;
  previewFile?: File;
};
function TamperRegions({ report, previewFile }: { report: ReportData; previewFile?: File }) {
  const result = report.modules.tamper;
  const [localFile, setLocalFile] = useState<File>();
  const [url, setUrl] = useState("");
  const [error, setError] = useState("");
  const file = localFile ?? previewFile;
  useEffect(() => {
    if (!file) return;
    const preview = URL.createObjectURL(file);
    setUrl(preview);
    return () => URL.revokeObjectURL(preview);
  }, [file]);
  if (!result?.regions?.length || !result.map_png || !result.original_size) return null;
  const [width, height] = result.original_size;
  async function selectOriginal(original?: File) {
    if (!original) return;
    setError("");
    try {
      const hash = await crypto.subtle.digest("SHA-256", await original.arrayBuffer());
      const fingerprint = Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
      if (fingerprint !== report.sha256) {
        setError("请选择当时上传的同一张图片，让标记准确叠加。");
        return;
      }
      setLocalFile(original);
    } catch {
      setError("本次无法校验本地图片，可以继续查看下方的异常图。");
    }
  }
  return (
    <section className="tamper-regions" aria-label="异常标记">
      <figure>
        <div className="tamper-map" style={{ aspectRatio: width / height }}>
          <img src={url || result.map_png} alt={url ? "本次核验图片" : "图片异常检测图"}
            onLoad={(event) => {
              const { naturalWidth, naturalHeight } = event.currentTarget;
              if (url && (naturalWidth !== width || naturalHeight !== height)) {
                setUrl("");
                setError("当前图片显示尺寸和检测记录不一致，请在异常图上查看标记。");
              }
            }} />
          {result.regions.map(({ box: [x1, y1, x2, y2] }, index) => (
            <span className="tamper-region" key={index} aria-hidden="true" style={{
              left: `${x1 * 100}%`, top: `${y1 * 100}%`,
              width: `${(x2 - x1) * 100}%`, height: `${(y2 - y1) * 100}%`,
            }} />
          ))}
        </div>
      </figure>
      {!url && (
        <label>选择当时上传的图片查看标记
          <input type="file" accept="image/*" onChange={(e) => { void selectOriginal(e.target.files?.[0]); e.target.value = ""; }} />
        </label>
      )}
      {error && <p role="alert">{error}</p>}
    </section>
  );
}
function isImageReport(report: ReportData) {
  return !!(report.modules.image || report.modules.tamper);
}
function FraudRiskReasons({risk}: {risk: NonNullable<ReportData["fraud_risk"]>}) {
  return <dl className="risk-reasons">
    <div><dt>合成线索</dt><dd>{risk.synthesis}</dd></div>
    <div><dt>诈骗话术</dt><dd>{risk.language}</dd></div>
  </dl>;
}
function ImageReport({report, onUpdate}: Props) {
  const title = report.summary;
  const showMarks = title === "建议核查" || title === "优先核查";
  const image = showMarks && report.marked_jpeg;
  const currentRisk = report.fraud_risk;
  const showImageFindings = !currentRisk?.language_reason || currentRisk.synthesis === "发现线索" || image;
  return (
    <section className={"image-report" + (image ? " image-report-with-preview" : "")} aria-label="图片核验报告">
      <div className="report-top">
        <div>
          <h1 className={showMarks ? "image-report-alert" : undefined}>{title}</h1>
          <p className="page-intro">{report.filename}</p>
        </div>
        <a className="report-pdf-export" href={`/api/cases/${encodeURIComponent(report.id)}/pdf`} download>导出 PDF</a>
      </div>
      <div className="image-report-body">
        {image && (
          <figure className="image-report-marked">
            <img className="image-report-preview" src={`data:image/jpeg;base64,${image}`} alt="用框标记的图片核验线索" />
          </figure>
        )}
        <div className="image-report-guidance">
          <h2>内容分析</h2>
          {showImageFindings && <p>{report.image_risk?.findings?.join("") || "可根据材料来源和原始记录核对关键信息。"}</p>}
          {currentRisk?.language_reason && <p>{currentRisk.language_reason}</p>}
          {currentRisk && <FraudRiskReasons risk={currentRisk} />}
          <h2>下一步</h2>
          <p>{currentRisk?.next_step || report.image_risk?.next_step || "找到图片的原始文件或最早发布的版本，核对关键内容。"}</p>
        </div>
      </div>
      {!!report.chat_analysis?.signals.length && <details className="card image-text-review">
        <summary>查看需要核实的原话</summary>
        {report.chat_analysis.signals.map((signal, index) => <blockquote key={index}>{signal.quote}</blockquote>)}
      </details>}
      {report.ocr?.text && <article className="image-text-review"><ChatTextReview report={report} onUpdate={onUpdate} /></article>}
    </section>
  );
}
function BatchComparison({ reports, selected, onSelect }: {
  reports: ReportData[];
  selected: string;
  onSelect: (report: ReportData) => void;
}) {
  const columns = ["video", "audio"].filter((key) => reports.some((report) => key in report.modules));
  return (
    <section className="card batch-comparison" aria-labelledby="batch-comparison-title">
      <h2 id="batch-comparison-title">材料对比</h2>
      <div className="table-wrap">
        <table>
          <thead><tr><th scope="col">文件</th><th scope="col">核验提示</th>
            {columns.map((key) => <th key={key} scope="col">{names[key]}</th>)}
          </tr></thead>
          <tbody>
            {reports.map((report) => (
              <tr key={report.id}>
                <th scope="row">
                  <button type="button" className="text-button" aria-current={report.id === selected ? "true" : undefined}
                    onClick={() => onSelect(report)}>{report.filename}</button>
                </th>
                <td>{report.summary}</td>
                {columns.map((key) => {
                  const module = report.modules[key];
                  const signal = module && moduleSignal(module);
                  const label = !signal || module.status === "disabled" ? "未检查"
                    : signal.level === "unavailable" ? "未完成"
                      : module.regions?.length ? `标出 ${module.regions.length} 处异常`
                        : signal.level === "alert" ? "达到提醒线" : "未达提醒线";
                  return <td key={key}>{label}{module?.score !== undefined && module.status === "completed"
                    ? ` · ${module.score.toFixed(3)}` : ""}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
export default function Report({bundle, onSelect, ...props}: Props & {
  bundle?: ReportData[];
  onSelect?: (report: ReportData) => void;
}) {
  const imageReport = isImageReport(props.report);
  return (
    <>
      {bundle && bundle.length > 1 && onSelect && (
        <BatchComparison reports={bundle} selected={props.report.id} onSelect={onSelect} />
      )}
      {imageReport ? (
        <ImageReport key={props.report.id} {...props} />
      ) : props.report.scene === "chat" ? (
        <ChatReport {...props} />
      ) : (
        <MediaReport {...props} />
      )}
      {!imageReport && <AgentReview report={props.report} />}
    </>
  );
}
function MediaReport({ report, onUpdate, previewFile }: Props) {
  const modules = Object.entries(report.modules).filter(([key, m]) => key === "tamper" || m.status !== "disabled");
  const alerts = modules.filter(([, m]) => moduleSignal(m).level === "alert");
  const tamperRisk = alerts.some(([key]) => key === "tamper");
  const hasRegions = !!report.modules.tamper?.regions?.length;
  const skippedTamper = modules.some(([key]) => key === "image") &&
    (!report.modules.tamper || report.modules.tamper.status === "disabled");
  const originalMaterial = modules.some(([key]) => key === "image")
    ? "找原图和最早的提交或发布记录，对照报告提示的画面线索。"
    : "找到原始录音或视频，对照报告提示的片段与发布记录。";
  useEffect(() => {
    let saved: Map<HTMLDetailsElement, boolean> = new Map();
    const before = () => {
      document
        .querySelectorAll<HTMLDetailsElement>(".report-record")
        .forEach((el) => {
          saved.set(el, el.open);
          el.open = true;
        });
    };
    const after = () => {
      saved.forEach((open, el) => (el.open = open));
      saved.clear();
    };
    addEventListener("beforeprint", before);
    addEventListener("afterprint", after);
    return () => {
      removeEventListener("beforeprint", before);
      removeEventListener("afterprint", after);
    };
  }, []);

  return (
    <>
      <div className="report-top">
        <div>
          <p className="eyebrow">发现了什么</p>
          <h1 className={report.summary === "优先核查" || report.summary === "建议核查" ? "image-report-alert" : undefined}>{report.summary}</h1>
          <p className="page-intro">
            {report.filename} ·{" "}
            {new Date(report.created_at).toLocaleString("zh-CN")}
          </p>
          {report.timings?.total_seconds !== undefined && (
            <small>
              本次处理 {report.timings.total_seconds.toFixed(1)}{" "}
              秒，排队和上传另计。
            </small>
          )}
        </div>
        <div className="toolbar">
          <a className="report-pdf-export" href={`/api/cases/${encodeURIComponent(report.id)}/pdf`} download>导出 PDF</a>
          <button onClick={focusQuestions}>问问真鉴 ↓</button>
          <button onClick={() => downloadReport(report)}>下载检测记录</button>
          <button onClick={() => window.print()}>打印</button>
        </div>
      </div>
      {modules.some(
        ([k, m]) =>
          k === "image" &&
          m.source?.version === "qinan-smaug-whole-r1-20261111",
      ) && (
        <p className="notice analysis-incomplete">
          这是旧版低阈值报告，可能过度提醒。请重新上传查看当前不确定区间和三视图数据；原始记录未改分。
        </p>
      )}
      {report.fraud_risk ? <FraudRiskReasons risk={report.fraud_risk} /> : <article
        className={"result-banner " + (alerts.length ? "alert" : "uncertain")}
      >
        <div>
          <span className="result-icon" aria-hidden="true">
            {alerts.length ? "!" : "?"}
          </span>
          <div>
            <h2>
              {hasRegions
                ? "有局部区域需要复核"
                : tamperRisk
                ? "局部篡改分数达到提醒线"
                : alerts.length
                ? alerts.map(([k]) => names[k] || k).join("、") +
                  "出现了合成信号"
                : modules.some(
                      ([, m]) => moduleSignal(m).level === "unavailable",
                    )
                  ? "部分材料未完成检查，请查看分项原因"
                  : "本次未检出明确合成信号"}
            </h2>
            <p>{tamperRisk ? "局部异常已计入 AI 内容核验的风险提示。请对照原图核对，普通编辑也可能触发。"
              : "结果反映这份材料的检测线索，来源和用途需要结合原始记录核实。"}</p>
            {skippedTamper && <p>局部篡改未检测，请使用原图重新核验。</p>}
          </div>
        </div>
      </article>}
      <TamperRegions report={report} previewFile={previewFile} />
      <section className="report-evidence" aria-labelledby="report-evidence-title">
        <h2 id="report-evidence-title">依据是什么</h2>
        <div className="report-modules">
          {modules.map(([key, m]) => {
            const s = moduleSignal(m);
            return (
              <article className={"card module signal-" + s.level} key={key}>
                <div className="module-top">
                  <h2>
                    {m.method === "temporal-sequence"
                      ? "视频时序换脸检查"
                      : names[key] || "材料检查"}
                  </h2>
                  <span className={"signal-label " + s.level}>
                    {s.level === "alert"
                      ? "需要警惕"
                      : s.level === "uncertain"
                        ? "仍需核实"
                        : "无法判断"}
                  </span>
                </div>
                <h3>
                  {key === "tamper" && s.level === "alert"
                    ? "发现局部篡改风险"
                    : key === "tamper" && s.level === "uncertain"
                      ? "未达到局部篡改提醒线"
                    : key === "audio" && s.level === "uncertain"
                    ? "本次未检出合成特征"
                    : key === "image" &&
                        s.level === "uncertain" &&
                        m.score !== undefined &&
                        m.sensitivity_threshold !== undefined &&
                        m.score >= m.sensitivity_threshold
                      ? "弱线索，证据不足"
                      : s.title}
                </h3>
                {key === "audio" && (
                  <p>
                    直接分析声音，不依据说话内容判断。
                    {m.analyzed_seconds !== undefined
                      ? `已分析 ${m.analyzed_seconds.toFixed(1)} 秒录音。`
                      : ""}
                  </p>
                )}
                <p className="plain-explanation">
                  {key === "tamper"
                    ? m.status === "completed"
                      ? "局部异常可作为复核线索，建议与原图对照。"
                      : m.note || "本次没有完成局部篡改检查。"
                    : s.level === "unavailable"
                    ? key === "audio"
                      ? m.failure_stage === "model"
                        ? "音轨已读取，但声音模型未完成；请查看下方独立内容检查。"
                        : m.note || "未取得可检查的音轨，请查看具体原因。"
                      : key === "video"
                        ? "没有取得适合检查的人脸画面。"
                        : "这份材料暂时无法检查。"
                    : s.level === "alert"
                      ? key === "audio"
                        ? `${s.flagged}段声音出现合成信号，可对照原始录音和对应片段。`
                        : key === "video"
                          ? "画面中发现了可能的合成或换脸线索。"
                          : "图片出现较强合成信号，请核对原图来源。"
                      : "仍需核实来源。"}
                </p>
                {m.segments && (
                  <details className="audio-detail">
                    <summary>看看哪些声音片段需要注意</summary>
                    {m.segments.map((part, i) => {
                      const high = part.score >= (part.threshold ?? 0.5);
                      return (
                        <div
                          className={
                            "audio-interval " + (high ? "alert" : "uncertain")
                          }
                          key={i}
                        >
                          <b>
                            {part.start.toFixed(0)}–
                            {(part.end ?? part.start + 5).toFixed(0)}秒
                          </b>
                          <span>{high ? "有合成信号" : "还不能确认"}</span>
                        </div>
                      );
                    })}
                  </details>
                )}
                <DetectionEvidence kind={key} module={m} />
              </article>
            );
          })}
        </div>
        <p className="score-caption">红色表示达到该项提醒线。黄色表示仍需核实。</p>
        {(report.transcript || report.speech_analysis) && (
          <SpeechContent report={report} onUpdate={onUpdate} />
        )}
      </section>
      <article className="card final-steps">
        <h2>下一步怎么核实</h2>
        {report.fraud_risk?.next_step ? <p>{report.fraud_risk.next_step}</p> : <>
        <p>
          <span className="step">1</span>
          {modules.length ? originalMaterial : "找到原件和最早的提交或发布记录。"}
        </p>
        <p>
          <span className="step">2</span>
          从原业务系统、原发布方或自行找到的可信渠道核对，再结合场景处理。
        </p>
        </>}
        <button className="primary" onClick={focusQuestions}>
          结合报告提问 ↓
        </button>
        <details className="report-record">
          <summary>检测记录</summary>
          <p>记录编号：{report.id.slice(0, 8)}</p>
          <p>原始上传材料已处理并删除。详细检测数据可用上方按钮下载。</p>
        </details>
      </article>
    </>
  );
}
