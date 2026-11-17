# 环境配置与部署复现

## 适用环境

已实际运行环境为 Windows x64、Python 3.10.21。项目内随部署提供的 OCR、MMCV、DAF 扩展针对 CPython 3.10，不能使用本机默认 Python 3.13。CPU 可执行推理；CUDA 为可选优化，需使用匹配的 torch、torchvision、torchaudio 组合。不同硬件耗时不同。

## 获取与安装

```powershell
git clone https://github.com/Sy-hjh/TruthLens.git
cd TruthLens
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` 是主依赖；`requirements-agent.txt` 是隔离 Agent 依赖；`requirements-dev.txt` 是开发依赖。Agent 按 `setup_agent.ps1` 安装至 `.agent-packages`，避免覆盖检测器运行库。主依赖包含 DAF 导入所需 albumentations 1.3.1，但不替代 MMCV 独立环境。

前端已构建，日常运行不需要 Node.js。修改前端时使用支持 `--experimental-strip-types` 的 Node.js 22.6 或更新版本，执行：

```powershell
cd web
npm ci
npm run typecheck
npm test
npm run build
```

前端依赖通过 `web/package-lock.json` 固定。不要以安装成功代替功能测试。

## 模型与独立运行资源

`docs/model-resource-manifest.json` 记录当前使用资源的相对路径、字节数及 SHA256；`models/active-*.json` 指定当前检测器。大型模型不提交 Git，资源来源和许可见各模型 source.json、README 及 THIRD_PARTY.md。

从当前已验证部署复制资源时，保持路径不变：models/community、provided-image-head、fused、daf、truthlens-ast-qwen、gend-clip、asr_zh、advisor。复制 runtime/forensics-pilot/daf-torch、daf-helpers、runtime/ocr-packages，以及模型所引用的 vendor/FUSED 与 vendor/OSTF 推理源码。不要复制账号数据库、初始化码或在线助手密钥。

部分模型可用现有下载脚本准备，例如 `python download_models.py asr_zh`、`python install_gend.py`、`python install_chat_ocr.py`、`python install_advisor.py`。脚本可能包含历史选型；当前启用项应以 active 配置及资源清单为准。当前仓库不提供所有权重和二进制的一键公开下载，不宣称纯 git clone 即可完整推理。

## 环境变量与可选在线服务

`.env.example` 为变量模板；程序不会自动读取 .env。可在 PyCharm Run Configuration 的 Environment variables 或启动终端中设置 HF_HOME、HF_HUB_DOWNLOAD_TIMEOUT。bootstrap.py 默认将缓存放在 runtime/cache。不要把实际凭据写入模板。

默认本地模式无需 API 密钥。可选在线问答在本机创建 runtime/companion-model.json，字段为 enabled、base_url、model、api_key；api_key 只放运行机。此配置和整个 runtime 均被 Git 忽略。

## 启动与检查

```powershell
.\.venv\Scripts\python.exe run.py --host 127.0.0.1 --port 8010
```

访问 http://127.0.0.1:8010，注册账号。管理员首次配置使用 runtime/admin-setup.txt 一次性码，不能公开。局域网演示改为 `--host 0.0.0.0`，手机通过电脑 WLAN IPv4 访问；公网部署需另配 HTTPS 和评审账号。

检查 `/api/health`，再上传已知对照素材验证实际推理。六份本机素材的测试记录见 `docs/demo-regression-summary.json`；精选样本不构成整体准确率。缺失资源时需显示未完成，不能当作真实。终端按 Ctrl+C 停止；8010 被占用时确认旧进程归属后停止。

## 常见故障

- NumPy C 扩展无法导入：核对 Python 3.10 与 cp310 二进制，不要混用 Python 3.13。
- DAF 未完成：检查 albumentations、vendor/OSTF 和独立 MMCV/PyTorch 目录；主环境 torch 不等于 DAF 环境。
- 模型不可用：按资源清单核对路径及 SHA256，不能只复制 active 配置。
- GitHub 下载失败：检查本机网络，保留失败状态，不关闭证书验证。
- 没有声音/转写：检查原视频音轨、解码依赖和 ASR 权重；声音检查与内容检查分别判断。
