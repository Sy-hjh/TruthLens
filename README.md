# TruthLens 真鉴

参赛团队：湖舟行；学校：大连东软信息学院；队长：胡瑾慧；队员：周宇航、陈浩翔。项目此前未发表或获奖。参赛架构、运行环境与提交说明见 [README_参赛提交说明.md](README_参赛提交说明.md)；录屏点击步骤及材料清单见 `submission/录屏与提交操作指南.md`。

真鉴是面向多行业的 AI 内容核验 Web 应用。用户可以上传图片、音频、视频或聊天截图，查看检测线索、下一步核实建议并导出 PDF。小鉴助手提供对话式核验与资料检索。管理员可以管理账号、模型检测阈值、案例、知识库和报告保留期限。

## 启动

1. 在 Windows 上解压后进入 `qinan`。首次使用时，在 PowerShell 运行 `powershell -ExecutionPolicy Bypass -File .\setup.ps1` 安装 Python 依赖。使用 GPU 时，按目标电脑的驱动安装相互兼容的 PyTorch、TorchVision 和 TorchAudio。
2. 双击 `start.cmd` 打开本机网页，使用 `stop.cmd` 停止。也可以在终端运行 `.venv\Scripts\python.exe run.py`，然后访问 [真鉴首页](http://127.0.0.1:8010/)。
3. 在首页注册普通账号。在 [管理后台](http://127.0.0.1:8010/#admin) 点击「首次配置管理员」，使用首启后在 `runtime/admin-setup.txt` 生成的一次性初始化码。账号、配置和报告各自在新部署的 `runtime` 目录创建。

包内已有 `frontend-next`，浏览页面无需安装 Node.js。修改前端源码后，在 `web` 中运行 `npm ci`、`npm run build`。运行 `npm test` 检查前端接口和检测提示边界。

## 启用完整检测

**完整版 ZIP** 已包含下列本地权重和当前 Web 检测实际使用的推理目录。建议使用 Windows x64 和 Python 3.10，随包附带的 DAF 及 OCR 二进制依赖适用此环境。先按启动步骤安装主 Python 依赖，再通过服务健康状态确认模型可用。小鉴的在线模式由部署者配置接口与密钥。

**轻量源码 ZIP** 包含当前模型配置、小型分类头、推理源码和公开示例。换电脑时，从已有可运行的部署复制下表中缺失的模型文件和推理目录到同一相对路径。仅启动页面、管理后台和浏览案例可先跳过此步骤。

| 模块 | 需要补齐的资源 |
| --- | --- |
| 整图检测 | `models/community/model.safetensors`。分类头已随包提供。 |
| FUSED 局部检测 | `models/fused/fused_opensdi.pth` 和 `models/fused/convnext.safetensors`。 |
| DAF 文字编辑 | `models/daf/srnet-tensors.pt`，以及匹配目标机器 Python 版本的 `runtime/forensics-pilot/daf-torch` 和 `daf-helpers`。 |
| 语音合成检测 | `models/truthlens-ast-qwen/model.safetensors`。Qwen 语音适配权重已随包提供。 |
| 视频检测 | 完整的 `models/gend-clip` 目录。有序视频分类头和协议已随包提供。 |
| 语音转写 | 完整的 `models/asr_zh` 目录。可使用 `download_models.py asr_zh` 获取项目配置的公开资源。 |
| 图片文字读取 | 运行 `install_chat_ocr.py`，或复制 `runtime/ocr-packages`。 |
| 小鉴问答 | 在线模式请自行创建 `runtime/companion-model.json`，填写 `enabled`、`base_url`、`model` 和 `api_key`。完整版内含 `models/advisor` 本地模型。如需 LangChain 代理依赖，运行 `setup_agent.ps1`。轻量版可用 `install_advisor.py` 准备本地模型。 |

补齐资源后，可访问 [服务健康状态](http://127.0.0.1:8010/api/health) 查看模型是否可用。模型来源与许可见 [第三方组件清单](docs/THIRD_PARTY.md)。`install_release.py` 用于复现 `release/release.json` 中的历史发布配置。

## 源码结构

- `backend/` 包含检测流水线、注册登录、管理员接口、报告和小鉴知识检索。
- `web/` 是 React 前端源码，`frontend-next/` 是运行时提供的页面文件。
- `models/`、`release/` 包含模型配置和随包附带的分类头。
- `docs/`、`reports/` 包含工程文档和公开评测摘要。
- `build_source_package.py` 可重新构建并校验源码压缩包，使用 `--full` 打包本地模型与推理依赖。

两个版本均排除账号和报告数据库、在线 API 密钥、用户上传素材与下载缓存。完整版中的 `runtime` 仅包含选定的推理依赖。检测结果提供待核实的线索，具体材料仍需结合原始记录和来源判断。
