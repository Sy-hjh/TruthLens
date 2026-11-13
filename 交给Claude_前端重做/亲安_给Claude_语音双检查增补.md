# 给Claude的增补：视频、音频双检查（2026-11-13）

这是用户在原前端交接包之后新增的正式需求，优先级高于旧文档中“不转写语音”的描述。后端已接入，不要只做演示。

1. 保留原视频画面检测和原声学合成检测；增加一条独立的“语音转文字→说话内容风险分析”。内容有借款/验证码等要求不代表声音AI；声音合成也不代表诈骗。不平均、不相加、不编造统一诈骗概率。
2. /api/analyze仍是原来的file/scene/context和异步任务协议，无新必填项。音视频报告新增transcript和speech_analysis。截图仍用ocr/chat_analysis，不能互相混淆。
3. transcript={status,text,raw_text?,source?,note?,original_text?,corrected?}；speech_analysis与chat_analysis结构相近，有status、signals、assessment（level/title/summary/reasons/cases/basis/version）、pattern等，并含input_basis=speech_transcript或user_corrected_transcript。完整可选字段参考更新的api.ts。
4. 页面保留各合成检测卡片，新增“说话内容风险”卡片，展示疑似套路标题、风险等级颜色、逐字转写证据、相似公开案例。alert红、attention橙、uncertain不直接说安全。总标题要能提示内容风险，即使声学阴性；合成卡自身仍说声学/画面结论，不把内容警报画成合成警报。
5. 有“核对声音转成的文字”折叠区及“文字听错了？修改并重查”。新增POST /api/cases/{id}/speech-text，FormData text（1–4000字符），返回完整Report。保存后替换当前完整对象，不改原有modules值。保留original_text和corrected标记，明确当前内容依据用户校正文字。不能称校正后是ASR实际听到的原话。
6. /api/cases/{id}/transcript仍是旧退休接口410，不能调用它。截图校正仍走/chat-text。
7. 语音转写/内容失败不能覆盖已完成的声学/视频结果；没音轨或静音时明确未取得声音，不制造文本或0分。旧报告没有speech_analysis时提示重新上传，不补造结果。没有数据的内容卡不显示安全。
8. 后端处理状态新增“正在转写声音并检查内容风险”；端到端比原版耗时更长，要保持异步轮询和重连，不用短超时自动重传。
9. 音视频不强制先合成阳性才做内容检查，正常真人语音也应检查内容。ASR和内容使用现有本地模型，前端不上传第三方。
10. 转写文字随报告存本机，原媒体处理后删除；应提示文字可在历史记录中删除。
11. 新参考组件SpeechContent.tsx已接入Report.tsx。请将此能力纳入你重做的前端，并与旧交接需求其他页面一并交付。当前仍不是实时共享屏幕功能。

附：新接口返回更多字段时，JSON导出保留完整报告。文字纠正请求可能较慢，采用较长超时，忙碌期间禁止重复保存；失败保留用户输入。主流程仍是上传文件，不新增登录或云服务。


## 2026-11-14 音轨故障和时间字段（向后兼容）
视频必须呈现画面、声音、说话内容三项独立结果；音频呈现声音和内容两项。语音转写与检测并行，不能用串行等待文案。
Report 可选 audio_info 包含 status、sample_rate、seconds，失败时 code、note。ModuleResult 可选 failure_stage（decode或model）、failure_code。声音模型失败不能写没有声音；音轨已读取则提示声音模型未完成，并继续展示独立文字检查。
Report 可选 timings：audio_decode_seconds、video_seconds、acoustic_seconds、asr_seconds、content_seconds、total_seconds。总耗时不包含排队上传，各项并行不能简单相加。旧报告没有这些字段时不要显示虚构耗时。
