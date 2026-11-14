import test from "node:test";
import assert from "node:assert/strict";
import { streamAdvice } from "./src/api.ts";
const result = {
  engine: "test",
  summary: "先核实",
  actions: [],
  sources: [],
  trace: [],
  mode: "langchain_agent",
  run_id: "x",
  duration_seconds: 1,
};
function install(t, response) {
  const old = globalThis.fetch;
  globalThis.fetch = async () => response;
  t.after(() => {
    globalThis.fetch = old;
  });
}
test("SSE tolerates UTF-8 characters split across chunks and CRLF boundaries", async (t) => {
  const raw =
    ": keep-alive\r\n\r\ndata: " +
    JSON.stringify({
      type: "step",
      tool: "search_guidance",
      status: "核对真实资料",
    }) +
    "\r\n\r\ndata: " +
    JSON.stringify({ type: "result", result }) +
    "\r\n\r\n";
  const bytes = new TextEncoder().encode(raw);
  install(
    t,
    new Response(
      new ReadableStream({
        start(c) {
          for (let i = 0; i < bytes.length; i += 3)
            c.enqueue(bytes.slice(i, i + 3));
          c.close();
        },
      }),
    ),
  );
  const events = [];
  const r = await streamAdvice(
    "public",
    "怎么核实",
    (s) => events.push(s),
    new AbortController().signal,
  );
  assert.equal(events[0].status, "核对真实资料");
  assert.equal(r.run_id, "x");
  assert.equal(events.length, 2);
});
test("SSE interruption cannot be labelled successful", async (t) => {
  install(t, new Response('data: {"type":"step","status":"读取中"}\n\n'));
  await assert.rejects(
    streamAdvice("x", "q", () => {}, new AbortController().signal),
    /连接中断/,
  );
});
test("server error event is shown rather than accepted as an answer", async (t) => {
  install(
    t,
    new Response('data: {"type":"error","message":"模型暂未完成"}\n\n'),
  );
  await assert.rejects(
    streamAdvice("x", "q", () => {}, new AbortController().signal),
    /模型暂未完成/,
  );
});
test("busy HTTP status preserves usable retry message", async (t) => {
  install(
    t,
    new Response(JSON.stringify({ detail: "已有建议生成任务，请稍后重试" }), {
      status: 429,
    }),
  );
  await assert.rejects(
    streamAdvice("x", "q", () => {}, new AbortController().signal),
    /稍后重试/,
  );
});
test("request carries current report and user question, not contact data", async (t) => {
  let init, url;
  const old = globalThis.fetch;
  t.after(() => (globalThis.fetch = old));
  globalThis.fetch = async (u, i) => {
    url = u;
    init = i;
    return new Response(
      "data: " + JSON.stringify({ type: "result", result }) + "\n\n",
    );
  };
  await streamAdvice(
    "r-123",
    "如何回拨",
    () => {},
    new AbortController().signal,
  );
  assert.equal(url, "/api/cases/r-123/agent-events");
  assert.deepEqual(JSON.parse(init.body), { question: "如何回拨" });
  assert.equal(init.method, "POST");
});
