# 数据与模型下载清单

不是所有模型文件都是“数据集”。当前已下载现成模型用于推理，小型素材用于功能/回归测试；没有进行新训练。大小为本次实际文件，MB按1,000,000字节计算，完整数据集的体积不拿本地子集冒充。

## 已下载素材

| 来源链接 | 本机内容/大小 | 用途 |
|---|---|---|
| [MINDS14](https://huggingface.co/datasets/PolyAI/minds14) | 中文训练分片32,357,378字节，提取6条真人电话音频 | 中文转写小样本与真人误报检查；CC-BY-4.0，非老人专用集 |
| [garystafford声音数据](https://huggingface.co/datasets/garystafford/deepfake-audio-detection) | 3真3假，共1,804,822字节 | 工程冒烟；与模型来源重叠，不能报告独立准确率 |
| 自制中文模拟语音 | 3条场景约0.271MB，另4条摘要提醒 | 明确标注合成，不能充当真人对照；来源和哈希见data/demo/source.json |
| 用户提供的两张原图 | 原路径与SHA仅存在本机私人回归记录 | 不公开、不上传第三方、不用于训练 |

获取素材脚本是download_chinese_samples.py、download_samples.py、make_demo_audio.py。不是运行网站的前置步骤，当前文件已经存在。

## 已下载权重

| 模块与来源链接 | 本机目录直接文件约大小 | 说明 |
|---|---|---|
| [VideoMAE换脸检测](https://huggingface.co/Vansh180/VideoMae-ffc23-deepfake-detector) | models/video，344.9MB | 16帧；原模型基于FF++ Deepfakes，不能覆盖所有生成视频 |
| [声音合成检测](https://huggingface.co/garystafford/wav2vec2-deepfake-voice-detector) | models/audio，1262.9MB | 中文真人存在误报 |
| [SigLIP图像检测](https://huggingface.co/Ateeqq/ai-vs-human-image-detector) | models/image，371.6MB | 对用户AI原图漏检已记录 |
| [TruFor](https://github.com/grip-unina/TruFor) | models/tamper，565.4MB（含260.9MB下载压缩包与解压权重） | 局部异常定位，非营利许可 |
| [中文Paraformer](https://huggingface.co/csukuangfj/sherpa-onnx-paraformer-zh-2024-03-09) | models/asr_zh，227.4MB | 默认本地转写，模型卡许可未明确 |
| [Whisper-small](https://huggingface.co/openai/whisper-small) | models/asr_small，971.4MB | 回退 |
| [Whisper-tiny](https://huggingface.co/openai/whisper-tiny) | models/asr，155.5MB | 保留旧回退 |

这些数值不包含分块下载缓存、Python依赖及vendor源码。确切revision与权重哈希见各目录source.json。下载器固定本次验证的版本，避免以后main更新导致来源与文件不一致。

## 暂不擅自下载训练集的原因

[DeepSpeak v1官方页](https://huggingface.co/datasets/faridlab/deepspeak_v1)列出约40GB、44小时，并要求申请和许可；[SWAN-DF官方发布页](https://zenodo.org/records/8365616)要求签署终端用户协议及机构资质。当前没有授权文件，不绕过门槛，也不拿非官方无来源镜像代替。下一步取得许可后，优先用按人物隔离的测试子集建立视频基线，再确定训练路线。

你现在先使用网站与内置中文演示，不需要下载几十GB数据，更不需要先运行旧CIFAKE训练。参赛时按真实来源引用，不把现成基础模型说成原创训练。
