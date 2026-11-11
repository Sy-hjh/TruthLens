# 复用来源与选择

前半保留历史选型；当前声学与聊天截图见本文最后一节及release/release.json。旧ASR不在当前业务流程启用。

本项目业务页面、任务编排、联系人和报告由当前工程实现；复用已有FastAPI、Transformers、OpenCV、FFmpeg和开源权重，不将整站开源项目直接包装参赛。

| 来源 | 用途 | 许可/限制 |
|---|---|---|
| https://huggingface.co/Vansh180/VideoMae-ffc23-deepfake-detector | 16帧时序画面分类 | 模型卡MIT；FF++ Deepfakes子集，不能外推所有生成视频 |
| https://huggingface.co/garystafford/wav2vec2-deepfake-voice-detector | 合成声音分类 | 模型卡Apache-2.0；英语训练；未知生成器泛化需测 |
| https://huggingface.co/datasets/garystafford/deepfake-audio-detection | 6条工程测试音频 | 具体卡与revision见data/sample-source.json；与训练来源重叠 |
| https://github.com/imageio/imageio-ffmpeg | 音轨提取与格式解码 | Python包BSD-2-Clause；打包FFmpeg具有独立许可，随发行包保留许可证 |
| https://github.com/huggingface/transformers | 模型推理 | Apache-2.0 |
| https://github.com/fastapi/fastapi | HTTP后端 | MIT |
| https://huggingface.co/openai/whisper-tiny | 本地语音转写 | Apache-2.0；识别错误与幻觉需要对照原音核实 |

## 调研但没有直接采用
- dima806/ai_vs_real_image_detection：模型卡明确提示旧训练数据导致概念漂移；继续沿用CIFAKE类模型不能解决之前用户反馈。
- nii-yamagishilab/wav2vec-small-anti-deepfake：有跨数据集研究，但官方示例依赖fairseq及自定义架构；不把它强行交给AutoModel后使用随机初始化分类器。
- MVSS-Net：没有采用。TruFor已在2.0接入，见下方。

下载模型时固定commit revision，不执行仓库远程代码。Transformers权重用safetensors。TruFor官方检查点按作者MD5验证，torch.load保持weights_only=True，仅显式允许所需NumPy标量类型，不启用任意pickle执行。
完整模型卡与来源保存在models各目录。正式参赛时保留这些说明和引用，不声称这些基础模型由我们原创训练。


## 2.0新增来源

| 来源 | 用途与许可 |
|---|---|
| https://huggingface.co/Ateeqq/ai-vs-human-image-detector | SigLIP整图分类，模型卡Apache-2.0；用户AI原图仍漏检 |
| https://github.com/grip-unina/TruFor | 局部编辑定位，作者非营利许可；原文在vendor/TruFor/TruFor_train_test/LICENSE.txt |
| https://www.grip.unina.it/download/prog/TruFor/TruFor_weights.zip | 作者权重，MD5 7bee48f3476c75616c3c5721ab256ff8 |
| https://huggingface.co/csukuangfj/sherpa-onnx-paraformer-zh-2024-03-09 | 默认中文ASR；模型卡未明确许可，不推定可商用 |
| https://github.com/k2-fsa/sherpa-onnx | ONNX本地转写运行时，Apache-2.0 |
| https://huggingface.co/openai/whisper-small | ASR回退，Apache-2.0 |
| https://huggingface.co/datasets/PolyAI/minds14 | 中文真人电话语音6条小样本，CC-BY-4.0，来源/标签见data/chinese-human/source.json |
| https://github.com/rany2/edge-tts | 通用中文模拟素材生成工具，LGPL-3.0；微软服务与声音许可独立，不冒充真人克隆授权 |

TruFor引用：Guillaro等，TruFor: Leveraging all-round clues for trustworthy image forgery detection and localization，CVPR 2023。项目保留原始LICENSE和作者文件。本项目教育研究范围使用，不转售权重或宣称商用授权。

## 3.0来源与本地改进（2026-11-11）

| 来源 | 用途与限制 |
|---|---|
| https://huggingface.co/zodumair/sifta-deepfake-detector | X-CLIP人脸时序模型，研究用途及上游数据限制；复现作者4组8帧、JPEG92与温度，不宣称自研基础编码器 |
| https://huggingface.co/eliya/forensics_0.3B_xlsr_wild_deepfake_classifier | 2026声音候选，CC-BY-NC-4.0。严格加载全部推理参数，仅移除作者架构未引用的四个projection张量；不执行原CLI的pickle回退 |
| https://huggingface.co/Qwen/Qwen3-0.6B | 本地受限解释，Apache-2.0；不是媒体真伪鉴定器，不读取家人号码 |
| https://github.com/opencv/opencv_zoo | YuNet人脸定位，MIT；不进行人物身份匹配 |
| https://huggingface.co/datasets/kontur-ai/rtfs-10k | CC-BY-SA-4.0；真实与inswapper/uniface视频，源YouTube ID划分，不声称人物身份隔离 |
| https://huggingface.co/datasets/TristanYan/FraudBench | CC-BY-NC-SA-4.0；商品局部AI编辑诊断与独立类别训练，Negative是实际损坏的真实材料，不是假图标签 |
| https://huggingface.co/prithivMLmods/deepfake-detector-model-v1 | 实验性人脸帧模型，作者卡Apache-2.0；本机验证误报偏高，未启用 |
| https://huggingface.co/obuladinnesai/car-damage-photo-integrity-v9 | 汽车局部编辑候选，作者卡Apache-2.0，上游数据限制独立；商品迁移漏检偏高，未启用 |
| https://react.dev/ / https://vite.dev/ | React + TypeScript + Vite自建前端；源码没有直接包装第三方整站 |

基础权重、数据许可和作者算法与本项目自建网页、编排、校准层、复核流程分别署名。保留固定revision、哈希和原始README。源码包不分发私人素材、联系人、数据库或整套训练数据；没有代替团队公开仓库或接受数据集人工审核协议。

## 2026-11-11调整
- 当前视频采用[yermandy/GenD_CLIP_L_14](https://huggingface.co/yermandy/GenD_CLIP_L_14)，MIT模型卡，固定revision与哈希见release/release.json；上游数据限制独立。参考[GenD WACV2026](https://github.com/yermandy/GenD)配对来源与归一化特征方法，8帧人脸均值；不执行远程模型代码。
- [B-Free](https://github.com/grip-unina/B-Free)官方非营利许可、[Detectra](https://huggingface.co/TensorFold/detectra-v1) MIT：局部改图诊断未通过，没有启用。保留作者源码和许可证。
- [Smaug](https://huggingface.co/abacusai/Smaug-AI-Image-Detector) Apache-2.0模型卡；三视图整图生成候选，使用独立依赖，不执行远程代码；局部修改能力不作保证。
- 新闻标题、日期与来源链接来自[12321举报中心](https://12321.cn/warn)、中央网信办和民政部公开提示；防范提醒是项目维护的主题提示，不假称自动获得案件全文。


## 声学与截图后续版本

- [VeriSpoof-Plus](https://huggingface.co/AustinXiao/VeriSpoof-Plus)：固定revision ef5b12112da17e0949b5e19fe0f9f198c9570fd9，模型卡发布日期2026-11-04；CC-BY-NC-4.0权重，Apache-2.0源码，NOTICE保留。直接声学原生检测，不转写。源码在vendor/verispoof；运行时只允许本地safetensors，禁远程代码。
- [RVCBench-Cloned-Speech](https://huggingface.co/datasets/Nanboy/RVCBench-Cloned-Speech)：revision 365897b08925e241672731f25bcb5edc5857417f，CC-BY-NC-4.0及各生成器附加条款。数据README与NOTICE在data/clone-bench。本次3910段中文含200真人、3710参考声音克隆，不是自行虚构的合成标签。
- [Qwen3-ASR-1.7B-hf](https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf)：revision bcd2b5b7f32b480ab5790554cfa8347f246a14f3，仅用于VeriSpoof匹配的本地架构配置、梅尔声学预处理配置，不下载其转写权重，不做语音转写。
- [RapidOCR](https://github.com/RapidAI/RapidOCR)：3.10.0固定PyPI包，自带PP-OCRv6模型；Apache-2.0与MODEL_LICENSES.md保留vendor/chat-ocr。检测时纯本机。
- [Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B)：沿用固定版本Apache-2.0本地权重，仅用于聊天截图文字要求解读；不识别声音、不确认身份。
- XLS-R/AASIST作者权重及原许可证继续保留，当前只对声学主模型阴性复查，阈值0.70；版本与SHA见release/release.json。基础数据/权重不冒称团队原创。

- 当前截图理解：[Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B)，固定70d244cc86ccca08cf5af4e1e306ecf908b1ad5e，Apache-2.0，本地两片safetensors严格校验。旧0.6B为历史实验；新版只选择原文编号，不把文字分析包装成AI作者识别。

## 本轮文字训练与论文
- ScamGen：作者Mendeley公开文本，https://data.mendeley.com/datasets/dkypjhkmgb/1 ，CC-BY-4.0。只取指定文本成员，按作者Hard划分，模型与报告保留来源署名。
- google-bert/bert-base-chinese：官方固定8f23c25b06e129b6c986331a13d8d025a92cf0ea，Apache-2.0，仅冻结语义对比，未上线。
- quanshiyun/anti_fraud_dataset：固定6a53ae5d5af88b4f01408396d9a954dbeebb92c4，作者卡GPL-3.0，仅下载待审计，未参与本轮训练。
- 用户提供的两篇CAJ仅本地研究阅读，转换副本在runtime/papers，不加入比赛源码包。
