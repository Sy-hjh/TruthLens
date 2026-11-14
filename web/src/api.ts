export interface Source {
  repo?: string;
  version?: string;
}
export interface Segment {
  start: number;
  end?: number;
  threshold?: number;
  score: number;
  signal?: string;
  source?: Source;
}
export interface ModuleResult {
  status: string;
  failure_stage?: string;
  failure_code?: string;
  method?: string;
  note?: string;
  score?: number;
  threshold?: number;
  sensitivity_threshold?: number;
  views?: { label: string; score: number; logit?: number }[];
  sampling?: {
    width: number;
    height: number;
    boxes: number[][];
    distinct_regions: number;
  };
  secondary_check?: {
    score: number;
    threshold: number;
    source?: Source;
  } | null;
  source?: Source;
  segments?: Segment[];
  map_png?: string;
  analyzed_seconds?: number;
  analysis_basis?: string;
  moments?: {
    start: number;
    end?: number;
    score: number;
    frame_indices?: number[];
    input_frames?: number;
  }[];
  detector_scores?: Record<string, number>;
}
export interface Report {
  timings?: Record<string, number>;
  audio_info?: {
    status: string;
    seconds?: number;
    note?: string;
    code?: string;
  };
  id: string;
  filename: string;
  created_at: string;
  summary: string;
  scene?: string;
  context?: string;
  sha256: string;
  modules: Record<string, ModuleResult>;
  ocr?: { text: string; note?: string };
  chat_analysis?: {
    assessment?: {
      level: string;
      title: string;
      summary: string;
      basis: string;
      cases: {
        title: string;
        publisher: string;
        date: string;
        url: string;
        summary: string;
        connection: string;
      }[];
    };
    status: string;
    summary?: string;
    extraction_status?: string;
    pattern?: {
      status: string;
      level: string;
      title: string;
      patterns: { label: string; score: number }[];
      note?: string;
      version: string;
    };
    signals: {
      category: string;
      title: string;
      quote: string;
      context?: string;
    }[];
    note: string;
  };
  speech_analysis?: Report["chat_analysis"];
  transcript?: {
    status?: string;
    corrected?: boolean;
    text: string;
    note?: string;
    raw_text?: string;
  };
  phrases: {
    source?: string;
    context?: string;
    excerpt: string;
    category: string;
    note: string;
  }[];
  limitations: string[];
  next_steps: string[];
}
export interface Metric {
  n: number;
  real_count: number;
  fake_count: number;
  balanced_accuracy: number | null;
  real_false_positive_rate: number | null;
  fake_miss_rate: number | null;
}
export interface Evidence {
  experiments: {
    title: string;
    report: string;
    note: string;
    metrics: Metric;
    rejected: number;
  }[];
  releases: Record<string, string>;
  warning: string;
}
export interface Advice {
  engine: string;
  summary: string;
  actions: string[];
  sources: { id: string; title: string; url: string; snippet?: string }[];
  trace: { tool: string; status: string }[];
  note?: string;
}
export async function api<T>(
  url: string,
  options: RequestInit = {},
  timeout = 20000,
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, {
      ...options,
      signal: options.signal || controller.signal,
    });
    const data = await response.json();
    if (!response.ok)
      throw Error(
        typeof data.detail === "string"
          ? data.detail
          : "请求未成功，请稍后重试",
      );
    return data as T;
  } catch (error) {
    if (error instanceof TypeError)
      throw Error("没有连上TruthLens真鉴服务。请启动软件后再试。");
    if (error instanceof DOMException && error.name === "AbortError")
      throw Error("等待时间较长，请稍后在核验记录中查看。");
    throw error;
  } finally {
    clearTimeout(timer);
  }
}
export function downloadReport(report: Report) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(report, null, 2)], { type: "application/json" }),
  );
  const a = document.createElement("a");
  a.href = url;
  a.download = `TruthLens真鉴-${report.id}.json`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export interface AgentStep {
  type: string;
  tool?: string;
  status?: string;
  elapsed_seconds?: number;
  source_ids?: string[];
  message?: string;
  result?: AgentAdvice;
}
export interface AgentAdvice extends Advice {
  mode: string;
  run_id: string;
  duration_seconds: number;
  report_facts?: string[];
  question_note?: string;
  sources: (Advice["sources"][number] & { date?: string })[];
}
export async function streamAdvice(
  id: string,
  question: string,
  onStep: (step: AgentStep) => void,
  signal: AbortSignal,
): Promise<AgentAdvice> {
  const response = await fetch(
    "/api/cases/" + encodeURIComponent(id) + "/agent-events",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
      signal,
    },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw Error(body.detail || "建议服务暂时不可用，请稍后重试。");
  }
  if (!response.body)
    throw Error("当前浏览器不支持流式读取，请换用新版浏览器。");
  const reader = response.body.getReader(),
    decoder = new TextDecoder();
  let buffer = "",
    result: AgentAdvice | undefined;
  function process() {
    let edge: number;
    while ((edge = buffer.indexOf("\n\n")) >= 0) {
      const block = buffer.slice(0, edge);
      buffer = buffer.slice(edge + 2);
      const data = block
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).trimStart())
        .join("\n");
      if (!data) continue;
      let e: AgentStep;
      try {
        e = JSON.parse(data) as AgentStep;
      } catch {
        throw Error("核实结果格式有误，请重试。");
      }
      if (e.type === "error")
        throw Error(e.message || "建议没有完成，请重试。");
      if (e.type === "result" && e.result) result = e.result;
      onStep(e);
    }
  }
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      buffer = buffer.replace(/\r\n/g, "\n");
      process();
      if (done) break;
    }
    if (!result) throw Error("连接中断，建议尚未完成。请重试。");
    return result;
  } finally {
    await reader.cancel().catch(() => {});
  }
}
