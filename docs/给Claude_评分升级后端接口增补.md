# 后端评分升级接口增补（前端暂未改动）

旧接口全部保留，旧页面可继续使用。新增内容请等用户明确授权改前端再接入。

## 原建议接口

POST `/api/cases/{id}/advice`，JSON `{"question":"我应该怎么核实？"}`，1到200字。仍有engine、summary、actions、sources、trace、note。
新增mode（langchain_agent或retrieval_fallback）、run_id、selection、corpus、duration_seconds、agent_error、safety。不要把fallback写成Agent成功，不要把模型分数显示成诈骗概率。

## 新增接口

- GET `/api/agent/capabilities`：实际框架版本、工具、知识库版本和限制。
- POST `/api/cases/{id}/agent-review`：与建议接口相同请求，返回结构化结果。并发忙时429。
- POST `/api/cases/{id}/agent-events`：同样JSON，用fetch流读取SSE（原生EventSource不能直接POST）。每行`data: {...}`，空行分隔；冒号开头为心跳。type=step含tool/status/elapsed_seconds/source_ids；type=result含result；type=error含message。只展示执行步骤，不展示虚构思维链，不提前展示未经校验的生成文字。完成后停止加载；断线提示可重试，不宣称成功。
- POST `/api/cases/{id}/feedback`：JSON verdict为useful、not_useful、false_alarm、missed_risk之一；返回saved、used_for_training=false、note。同一报告最新反馈覆盖前次。可用于后续人工复核，不直接训练。
- GET `/api/agent/metrics`：运行与兜底计数、反馈汇总，不含原聊天，不是检测准确率。
- DELETE原报告接口同步清理Agent审计和反馈。

trace可包含plan、read_report、search_guidance、read_source、repair、output_guard、fallback_retrieval、complete。来源必须展示真实title/url/date，使用安全新窗口链接。旧报告缺少新字段时不要报错。

## 等待前端阶段的评分项

新进度/来源/反馈组件、统一状态与取消提示、手机适配、大字对比度、错误边界、性能测量、流式步骤渲染及真实老人试用；当前不能算完成。TypeScript和组件已有基础，但需对Claude新版本重新验收。旧首屏构建结果不可替代新前端验收。
