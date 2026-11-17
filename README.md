# TruthLens 真鉴

参赛团队：湖舟行；学校：大连东软信息学院；队长：胡瑾慧；队员：周宇航、陈浩翔。项目此前未发表或获奖。

## 技术架构

浏览器 React + TypeScript + Vite → FastAPI 鉴权与任务接口 → 单队列本地模型推理 → SQLite 报告存储 → RAG 检索与受限 Agent → 报告展示、问答和导出。

图片使用整图分类、FUSED 局部检查及 DAF 文字编辑检查；有声视频分别执行有序画面 GRU 检测、AST 声学检测和 ASR 转写内容分析。小鉴使用 Qwen 与受限工具生成有来源的核实建议。基础模型归原作者所有，团队实现应用、编排、适配及核验流程。

详细说明：[环境与部署](docs/ENVIRONMENT.md)、[架构与代码规范](docs/ARCHITECTURE.md)、[代码仓库要求验收](docs/REPOSITORY_ACCEPTANCE.md)、[资源清单](docs/model-resource-manifest.json)、[第三方声明](docs/THIRD_PARTY.md)。

真鉴是面向多行业的 AI 内容核验 Web 应用。用户可以上传图片、音频、视频或聊天截图，查看检测线索、下一步核实建议并导出 PDF。小鉴助手提供对话式核验与资料检索。管理员可以管理账号、模型检测阈值、案例、知识库和报告保留期限。

## 启动

1. 安装 Python 3.10 x64，克隆本仓库并进入仓库根目录。首次使用时，在 PowerShell 运行 `powershell -ExecutionPolicy Bypass -File .\setup.ps1` 安装 Python 依赖。使用 GPU 时，按目标电脑的驱动安装相互兼容的 PyTorch、TorchVision 和 TorchAudio。
2. 双击 `start.cmd` 打开本机网页，使用 `stop.cmd` 停止。也可以在终端运行 `.venv\Scripts\python.exe run.py`，然后访问 [真鉴首页](http://127.0.0.1:8010/)。
3. 在首页注册普通账号。在 [管理后台](http://127.0.0.1:8010/#admin) 点击「首次配置管理员」，使用首启后在 `runtime/admin-setup.txt` 生成的一次性初始化码。账号、配置和报告各自在新部署的 `runtime` 目录创建。

包内已有 `frontend-next`，浏览页面无需安装 Node.js。修改前端源码后，在 `web` 中运行 `npm ci`、`npm run build`。运行 `npm test` 检查前端接口和检测提示边界。

## 启用完整检测

**本 GitHub 仓库是源码交付**，不包含大型模型权重和 Windows 推理二进制环境。已提供当前模型选择配置与资源 SHA256 清单。小型适配头及其他权重按资源说明另行准备。推荐 Windows x64 和 Python 3.10。完整推理需按 [环境与部署](docs/ENVIRONMENT.md) 准备资源，不能将页面启动或健康接口资源检查等同于模型实测通过。

换电脑时，从已有可运行部署复制下表中缺失的模型与推理目录至同一相对路径，并依据资源清单核对哈希。没有资源的分支须保持不可用状态，不能伪造检测结果。

| 模块 | 需要补齐的资源 |
| --- | --- |
| 整图检测 | `models/community/model.safetensors`。分类头按资源清单另行准备。 |
| FUSED 局部检测 | `models/fused/fused_opensdi.pth` 和 `models/fused/convnext.safetensors`。 |
| DAF 文字编辑 | `models/daf/srnet-tensors.pt`，以及匹配目标机器 Python 版本的 `runtime/forensics-pilot/daf-torch` 和 `daf-helpers`。 |
| 语音合成检测 | `models/truthlens-ast-qwen/model.safetensors`。语音适配权重按资源清单另行准备。 |
| 视频检测 | 完整的 `models/gend-clip` 目录。有序视频分类头和协议见 release 目录。 |
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
