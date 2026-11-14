import type { ModuleResult } from "../api";
type Point = { label: string; score: number; threshold: number };
function RegionLayout({
  sampling: s,
}: {
  sampling: NonNullable<ModuleResult["sampling"]>;
}) {
  const scale = Math.min(280 / s.width, 180 / s.height),
    w = s.width * scale,
    h = s.height * scale,
    left = (340 - w) / 2,
    top = 15;
  return (
    <details>
      <summary>三个图块取自哪里？</summary>
      <svg
        style={{ maxWidth: 360, display: "block", margin: "12px auto" }}
        viewBox="0 0 340 225"
        role="img"
        aria-label="真实采样区域示意，不是AI异常位置"
      >
        <rect
          x={left}
          y={top}
          width={w}
          height={h}
          fill="#edf1ea"
          stroke="#7a897c"
        />
        {s.boxes.map(([x1, y1, x2, y2], i) => (
          <g key={i}>
            <rect
              x={left + x1 * scale}
              y={top + y1 * scale}
              width={(x2 - x1) * scale}
              height={(y2 - y1) * scale}
              fill="none"
              stroke={["#355f6c", "#b28438", "#6c5f91"][i]}
              strokeWidth="2"
            />
            <text x={left + x1 * scale + 5} y={top + y1 * scale + 15 + i * 13}>
              {i + 1}
            </text>
          </g>
        ))}
        <text x="15" y="219">
          框表示采样范围，不是发现伪造的位置
        </text>
      </svg>
      <p>
        检查3次，共{s.distinct_regions}
        个不同区域，区域可以重叠。数字对应下方图块。
      </p>
    </details>
  );
}
function Plot({ title, points }: { title: string; points: Point[] }) {
  const top = 22,
    bottom = 158,
    width = 640,
    left = 52,
    right = 620;
  const y = (s: number) =>
    bottom - Math.max(0, Math.min(1, s)) * (bottom - top);
  const x = (i: number) => left + ((right - left) * (i + 0.5)) / points.length;
  return (
    <section className="evidence-plot">
      <h4>{title}</h4>
      <svg
        viewBox={`0 0 ${width} 210`}
        role="img"
        aria-label={title + "：模型分数和触发阈值"}
      >
        {[0, 0.5, 1].map((v) => (
          <g key={v}>
            <line x1={left} x2={right} y1={y(v)} y2={y(v)} stroke="#dce3df" />
            <text x={left - 8} y={y(v) + 4} textAnchor="end">
              {v.toFixed(1)}
            </text>
          </g>
        ))}
        {points.length > 1 && (
          <polyline
            points={points.map((p, i) => `${x(i)},${y(p.score)}`).join(" ")}
            fill="none"
            stroke="#486d67"
            strokeWidth="2"
          />
        )}
        {points.map((p, i) => (
          <g key={i}>
            <line
              x1={x(i) - Math.min(30, 240 / points.length)}
              x2={x(i) + Math.min(30, 240 / points.length)}
              y1={y(p.threshold)}
              y2={y(p.threshold)}
              stroke="#a04e25"
              strokeDasharray="4 3"
              strokeWidth="2"
            />
            <circle
              tabIndex={0}
              cx={x(i)}
              cy={y(p.score)}
              r="4"
              fill={p.score >= p.threshold ? "#b34b40" : "#4c7a70"}
            >
              <title>
                {p.label}；分数{p.score.toFixed(4)}；阈值{p.threshold}
              </title>
            </circle>
            {points.length <= 12 && (
              <text x={x(i)} y={184} textAnchor="middle">
                {p.label}
              </text>
            )}
          </g>
        ))}
        <text x={left} y={204}>
          圆点：模型分数　虚线：该项提醒线（非真假概率）
        </text>
      </svg>
      <details>
        <summary>查看逐项数值</summary>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>采样位置 / 时间</th>
                <th>模型分数</th>
                <th>阈值</th>
              </tr>
            </thead>
            <tbody>
              {points.map((p, i) => (
                <tr key={i}>
                  <td>{p.label}</td>
                  <td>{p.score.toFixed(4)}</td>
                  <td>{p.threshold.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
export default function DetectionEvidence({
  kind,
  module: m,
}: {
  kind: string;
  module: ModuleResult;
}) {
  if (m.status !== "completed")
    return (
      <div className="evidence-panel">
        <h3>本项没有有效检测数据</h3>
        <p>{m.note || "未完成检测，不能展示分数或得出结论。"}</p>
      </div>
    );
  const threshold = m.threshold ?? 0.5;
  const primary = (m.segments || []).filter(
    (p) =>
      p.source?.repo !== "eliya/forensics_0.3B_xlsr_wild_deepfake_classifier",
  );
  const secondary = (m.segments || []).filter(
    (p) =>
      p.source?.repo === "eliya/forensics_0.3B_xlsr_wild_deepfake_classifier",
  );
  return (
    <div className="evidence-panel">
      <h3>查看本次检测依据</h3>
      <p>圆点是本次检测分数，虚线是提醒线。分数不能直接证明伪造。</p>
      {m.score !== undefined && (
        <dl className="evidence-numbers">
          <div>
            <dt>检测分数</dt>
            <dd>{m.score.toFixed(4)}</dd>
          </div>
          <div>
            <dt>提醒线</dt>
            <dd>{threshold.toFixed(4)}</dd>
          </div>
          {m.sensitivity_threshold !== undefined && (
            <div>
              <dt>复查起点</dt>
              <dd>{m.sensitivity_threshold.toFixed(4)}</dd>
            </div>
          )}
        </dl>
      )}
      {kind === "image" && m.sampling && <RegionLayout sampling={m.sampling} />}
      {kind === "image" && (
        <>
          <p>
            从同一张图裁取3个图块，分别检查AI生成信号后汇总。图块可能重叠。
            {m.sensitivity_threshold !== undefined &&
              ` ${m.sensitivity_threshold}–${threshold}为不确定区间，不能认定合成。`}
          </p>
          {m.views?.length ? (
            <Plot
              title="三个图块的检测结果"
              points={m.views.map((v) => ({ ...v, threshold }))}
            />
          ) : (
            <p>旧报告未保存视图分数，重新上传可查看；不补造历史数据。</p>
          )}
        </>
      )}
      {kind === "video" && (
        <p>
          {m.method === "temporal-sequence"
            ? "每段选取4个有序画面共同分析，最多检查4段，保留前后顺序。未检测口型同步；可能漏掉短暂替换。"
            : "此旧版按时间抽取画面分别检查，未使用联合时序或口型同步检测。"}
        </p>
      )}
      {kind === "video" &&
        (m.moments?.length ? (
          <Plot
            title={
              m.method === "temporal-sequence"
                ? "有序视频片段输出"
                : "视频采样帧输出"
            }
            points={m.moments.map((p) => ({
              label:
                p.end !== undefined
                  ? `${p.start.toFixed(1)}–${p.end.toFixed(1)}秒`
                  : p.start.toFixed(1) + "秒",
              score: p.score,
              threshold,
            }))}
          />
        ) : (
          <p>旧报告未保存逐帧分数，重新上传可查看。</p>
        ))}
      {kind === "audio" && (
        <>
          {primary.length > 0 && (
            <Plot
              title="声音分段检查"
              points={primary.map((p) => ({
                label: `${p.start.toFixed(1)}–${(p.end ?? p.start + 8).toFixed(1)}秒`,
                score: p.score,
                threshold: p.threshold ?? 0.5,
              }))}
            />
          )}{" "}
          {m.secondary_check && (
            <Plot
              title="第二个声音模型复查（中间5秒）"
              points={[
                {
                  label: "中段复查",
                  score: m.secondary_check.score,
                  threshold: m.secondary_check.threshold,
                },
              ]}
            />
          )}{" "}
          {!m.secondary_check && secondary.length > 0 && (
            <Plot
              title="补充声学模型输出"
              points={secondary.map((p) => ({
                label:
                  p.end !== undefined
                    ? `${p.start.toFixed(1)}–${p.end.toFixed(1)}秒`
                    : p.start.toFixed(1) + "秒",
                score: p.score,
                threshold: p.threshold ?? 0.7,
              }))}
            />
          )}
          <p>分段检查声音，必要时由另一个模型复查。两个分数分别判断。</p>
        </>
      )}
    </div>
  );
}
