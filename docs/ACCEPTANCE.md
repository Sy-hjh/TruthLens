# 本轮验收证据（2026-11-11修订）

- reports/gend-final.json：180段计划、179可用，平衡准确率92.89%，误报5/60、漏检7/119，1段无可用人脸；不代表所有AI视频。
- reports/smaug-whole-final.json：634张整图生成留出测试97.32%，误报12/317、漏检5/317；阈值只用632张验证图拟合。不是局部P图准确率。
- reports/audio-mandarin-check.json：60组同文本真人/通用TTS诊断97.5%，不代表克隆声业务准确率。
- reports/manual-acceptance.json：15份真实HTTP上传。图片3/5（两个局部改图漏检）、视频6/6、声音4/4；只作功能回归，不作独立通用准确率。
- reports/delivery-verification.json：8份真实权重链路（含坏图/静音预期失败）、清理与隔离；23项后端/恢复检查。
- web/test-signals.mjs：7项阈值与不可用边界，涵盖0.739声音、1.0图片、低分黄色和非默认阈值。
- reports/deployment-http.json：实际8010上传、当前视频版本、静态资源、测试记录清理。
- reports/ui-practice-wrong.jpg：浏览器实际答错，红色错误与绿色正确。
- reports/ui-news.jpg：带发布日期、来源与原文入口。
- reports/ui-image-alert-final.jpg：新生成厨房图，旧模型漏检，新模型实际网页红色提醒。
- reports/pdf-contact-sheet.jpg：8页技术文档渲染检查。

生产构建与自动检查通过。本机启动器使用runtime/python-path.txt指定的CUDA Python，不再优先误用CPU虚拟环境。

浏览器截图来自工具当前窄视口，不宣称完成所有桌面/手机尺寸测试；真实拨号与打印仍需最终设备检查。技术PDF及源码供团队审阅，没有录制视频、公开或提交比赛。


## 最新声音与截图验收（替代上面的旧声音版本描述）

- reports/verispoof-test-channels.json：主声学模型624段/6名留出说话人；原音BA99.9155%、AAC98.3530%、电话99.3243%，仅32真人；传播变体同一录音，不独立累计。
- reports/voice-cascade-check.json：声学阴性复查的已观察集补充验证；不能作为新独立测试。
- reports/voice-data-audit.json：3910段完整，跨集合相同哈希/标签冲突0；按说话人隔离。
- reports/voice-resume-check.json：2+2步与连续4步权重完全相等、优化器恢复。
- reports/delivery-verification.json：本轮8份真实模型链路、29项自动检查。语音无转写/话术，静音无分数、坏图预期失败、原始上传清理。
- reports/chat-pipeline-check.json：独立截图OCR和原文约束语义分析；无声学结果。
- reports/chat-browser-proof.png、voice-real-browser-proof.png、voice-clone-browser-proof.png：真实浏览器上传，真人未检出、Qwen克隆红色、截图提字及对应要求。
- reports/voice-browser-acceptance.json：浏览器实际创建记录的API复核，声学纯波形标记、无转写/话术。
- tmp/pdfs/voice-doc-contact.png：更新后的8页PDF渲染检查。

旧audio-mandarin-check为通用TTS历史诊断，不再作为当前克隆声能力依据。没有重新取得用户原始私有录音，不宣称已重测它。小样本、未知上游重叠和局部P图漏检仍明确保留。


## 本轮用户误报、原文对齐与图表验收

- reports/backend-checks-final.json：32项后端/恢复检查；web/test-signals.mjs：9项边界检查。
- reports/report-trace-check.json：实际2份图像的三视图汇总与logit严格一致，视频8点均值一致，音频窗口时长有效。
- reports/image-review-policy.json：在已观察634图上复核强提醒边界和23图不确定区；不冒充新独立测试。
- reports/chat-semantic-review.json：10类已观察场景类别覆盖检查，不测通用准确率，也不能证明每条短引文语义充分。报告提供原始上下文并增加身份片段约束。
- 用户原失败记录保留OCR并在浏览器重新提交；实拍图新报告不再强提醒，但仅为不确定，不宣称已识别真实。合成图仍为较强输出。

以上是功能及策略修正，没有证明整套图片模型已达到真实业务可靠性。旧低阈值和文字小模型失败记录保留。

## 本轮新增范围
文字已进行ScamGen Hard训练和独立保留测试，五类70.44%，BERT对比65.01%，目前不满足90%目标，实验提示不能替代诈骗判断。录音条件16条稳定性检查不代表新独立准确率。网页文案、真实原话引用、修改重查和声学隔离需共同核验；旧提交材料未包含这一文字训练能力，介绍时以最新说明为准。
