# 当前数据与模型清单（2026-11-11声学升级）

| 来源 | 本地内容与实际大小 | 用途 |
|---|---|---|
| [RVCBench-Cloned-Speech](https://huggingface.co/datasets/Nanboy/RVCBench-Cloned-Speech) | data/clone-bench约1.03GiB，3910段中文：200真、3710参考声音克隆，40人19生成器 | 训练2544、验证742、测试624，按说话人隔离；不是整个公开多语言库大小 |
| [VeriSpoof-Plus](https://huggingface.co/AustinXiao/VeriSpoof-Plus) | models/verispoof约5.94GiB | 当前纯声学主模型，作者卡2026-11-04；固定似然比阈值0 |
| [XLS-R/AASIST](https://huggingface.co/eliya/forensics_0.3B_xlsr_wild_deepfake_classifier) | models/audio-forensics约1.18GiB | 主模型未检出时中间5秒复查，阈值0.70；也作为冻结编码器训练头 |
| [RapidOCR](https://github.com/RapidAI/RapidOCR) | runtime/ocr-packages，3.10.0包自带PP-OCRv6 | 聊天截图本机提字，不是语音转写 |
| [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B) | models/advisor，沿用已下载权重 | 仅分析截图文字中的要求、引用原文 |
| [GenD_CLIP_L_14](https://huggingface.co/yermandy/GenD_CLIP_L_14) | models/gend-clip，约1.22GB权重 | 当前人脸换脸画面检测 |
| [Smaug](https://huggingface.co/abacusai/Smaug-AI-Image-Detector) | models/smaug，约878MB权重 | 当前整图生成检测，不代表局部P图 |
| [MINDS14](https://huggingface.co/datasets/PolyAI/minds14)＋明确标注的通用TTS | 中文同文本60真/60假旧诊断 | 补充功能与领域检查，不代替现代参考声音克隆测试 |

GiB按1024³字节，GB按十亿字节；上表本地子集不冒充完整数据集。录音传播变体不是新增独立数据。固定revision、权重SHA、许可见release/release.json、各模型source.json、docs/THIRD_PARTY.md。

数据README、NOTICE及Fish/Higgs/XTTS附加许可已保留data/clone-bench/LICENSES。训练冻结编码器，仅更新分类头，31轮已完成、最佳21轮，未自动启用；模型选择理由与失败见docs/本轮修改记录.md。

当前C盘记录时约57GiB可用；主声学模型需要CUDA约6.4GB显存。不要同时开网站推理与大模型训练。运行方法只看根目录《现在只看这份.md》。旧下载表在docs/history/数据清单-声学升级前.md，旧ASR/TruFor不是当前声音流程。
