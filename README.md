# TruthLens 真鉴

**TruthLens真鉴——面向亲友冒充的多模态核验与反诈问答 Web系统**

已连接本地多模态模型和LangChain核实工作流的网页作品，不是静态原型。保留图像、视频、声学、语音内容、聊天截图、可信联系人、反诈练习与新闻、核验记录、导出与反馈。

## 直接启动

本机项目目录：`C:/Users/Lenovo/Documents/Codex/2026-11-07/wo/outputs/qinan`。
双击 `start.cmd`，访问 http://127.0.0.1:8010/ 。旧页面按Ctrl+F5刷新。停止用 `stop.cmd`。
路径名qinan保留是为了兼容训练和模型配置；客户界面统一使用TruthLens真鉴。

## 优先阅读

- `docs/TruthLens_融合设计与交付记录.md`：两个包的取舍、文件职责、接口、启动与复测。
- `docs/TruthLens_评分逐项对照与严格自评.md`：逐条评分依据、证据及未证实内容。
- `docs/TruthLens_老人试用任务单.md`：用户已答应实施的真实试用任务和空白记录表。

## 前端开发

```powershell
cd web
npm ci
npm run typecheck
npm test
npm run format:check
npm run build
```

构建写入frontend-next，由现有FastAPI服务提供；前端API使用相对路径，手机访问不指向手机自己的localhost。Three.js单独按需加载。

## 后端验证

```powershell
python -m unittest tests test_audio_isolation test_speed_audio test_speech_content test_text_patterns test_chat_assessment test_advisor test_domain test_image_regions test_checkpoint_io test_agent_upgrade test_truthlens_delivery
python verify_agent_upgrade.py --live
```

测试79项的日志、真实媒体回归、浏览器截图位于本机runtime和reports；源码包只带选定的公开验证摘要，不包含私有图片、联系人、历史数据库或大型权重。

## 新电脑与训练

此源码包不附所有预训练权重、数据集和node_modules。当前电脑已安装，可直接启动；新电脑需按原安装、下载脚本准备依赖与模型，不能把源码ZIP当作完整模型环境。
原安装/训练操作保留在 `docs/历史_亲安_README.md` 及原训练说明，训练脚本和冻结模型协议未被本轮前端替换。
LangChain依赖由setup_agent.ps1安装到独立.agent-packages。

## 真实边界

合成线索、可疑要求和身份核实是不同问题。检测分数不是诈骗概率。已有素材回归通过不能代表未知生成器的普遍准确率。真实老人试用、不同手机与浏览器实机、机构试点仍需参与者提供证据，不伪造满分或用户试用结论。未录演示视频、未发布公网。
