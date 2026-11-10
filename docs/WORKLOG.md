# 亲安：实施记录

## 2026-11-10 / 01 需求冻结
- 主要用户：老人。主场景：上传已录制的亲人求助视频；补充语音冒充、假专家宣传演示。
- 产品：手机/PC响应式网站，预留联系人回拨、核验记录、情境练习。
- 不声称读取微信通话，不自动拨号，不把模型分数当诈骗概率。
- 保留旧lensguard，新建qinan；复用其HTTP、历史和媒体模块，再替换产品流程。

## 02 模型路线
- 查阅VideoMAE换脸分类模型、Wav2Vec2合成语音模型及图像取证项目。
- 模型选择以兼容性、许可、推理与独立测试为依据，不沿用CIFAKE成绩证明能力。
- 候选：Vansh180/VideoMae-ffc23-deepfake-detector；garystafford/wav2vec2-deepfake-voice-detector。
- 尚未完成下载、推理、许可复核和效果评测，不能称为已接入。

## 记录规范
每一阶段记录：目的、修改文件、命令、结果、失败和取舍。只记录可复现的工程理由，不虚构实验和训练。

## 03 本机实现
- backend/app.py：单worker后台任务，任务轮询；原文件用临时目录保存，处理后删除；记录分模块结果，不平均成诈骗概率。
- backend/detector.py：VideoMAE 16帧片段；Wav2Vec2 16kHz音频，前30秒按10秒分段；顺序加载释放显存。
- frontend：适老字号、联系人本机存储、tel链接、浏览器语音朗读、三场景固定练习、历史删除及导出。
- 话术证据当前是透明的关键词规则，只分析手动描述；未冒充ASR或LLM。
- 图片生成和篡改定位还未接入，主动显示不可用。

## 04 下载与失败恢复
- python download_models.py：初始大文件断流，只得到约11MB；改为4MiB范围请求、8线程、每片重试及大小检查。固定revision和模型卡保留。
- pip下载imageio-ffmpeg停滞，改为install_ffmpeg.py从PyPI获取发行信息，分块下载，SHA256验证后解包；保持TLS验证，没有关闭证书检查。
- python download_samples.py：下载公开数据6条（3真3假），总计约1.72MiB；来源与revision写data/sample-source.json。与训练来源重叠，仅做工程验证。
- 未下载整套FF++：需要申请；不绕过申请，不将其他来源视频冒充合法获准数据。

## 05 已完成检查
- python tests.py：4项通过，涵盖页面/健康接口、非法/空上传、规则证据、SQLite增删。
- node --check frontend/app.js、python -m compileall -q backend：通过。
- python run.py：8010端口启动，HTTP健康接口可访问。
- 浏览器检查亲安页面与练习第一题，选择后显示解释及“下一题”。
- 模型下载未完成时健康接口显示未安装；不显示假就绪。

## 下一阶段
完成权重下载→python verify_models.py验证兼容性→实际HTTP文件上传测试→如失败先修复再报告。
中文、老人语音、压缩视频、未知生成器需要独立测试；本轮尚未训练，原因是没有独立领域数据支撑收益判断。

## 06 当前进度补记
- install_ffmpeg.py：分块发行包已下载，SHA256验证通过；真实FLAC成功解码83792样本（约5.237秒）。
- 公开6条音频下载完成，精确大小见data/sample-source.json。
- 视频模型约344.94MB、音频模型约1262.86MB；为避免大请求断流，拆成4MiB并发片段，断点片段可复用。增加LFS SHA256校验再启用模型。
- 调研拒绝将旧CIFAKE图片模型当作升级方案；拒绝将自定义fairseq模型错装成标准分类器而产生随机参数。
- 亲安独立端口8010；旧电商服务8000不修改、不删除。源代码文件用途列在README。

## 07 转写与评测路线
- 增加openai/whisper-tiny本地自动转写，使用自动语言识别，前30秒。自动文字与用户描述区分来源；转写错误不冒充原始事实。
- 增加evaluate_manifest.py，供授权、独立的真假素材清单评测；预测失败单列，不编造指标。
- 调研Deepfake-Eval-2024和deepsafe/evaluation-dataset。后者读取README时返回需认证授权，停止下载，没有绕过门槛或采用第三方镜像。
- 原始模型视频在GPU上完成推理；测试输入为16帧纯色，结果0.5144，仅说明结构兼容，不代表检测成绩。

## 08 端到端视频链路
- python verify_http.py --video-only：提交真实AVI文件→202后台任务→VideoMAE推理→报告查询→删除，已通过。
- 测试视频是运动色块，没有声音，因此音轨模块明确失败，视频结果仍保留；没有伪造出声音分数。
- Whisper-tiny对公开英语真实音频完成自动识别并输出文字；修正attention_mask传参，避免padding歧义。
- 音频包网络多次TLS断流：保留证书检查，增加带退避的重试，续用完整的4MiB缓存片段，未重新下载已校验的片段。

## 09 演示素材与失败记录
- 本机SAPI.GetVoices返回0x80045039；没有偷偷换用收费服务，没有声称生成成功。
- docs/DEMO.md提供三条模拟演示脚本与真人对照要求；中文素材尚需授权采集或可用生成器。
- 提供setup.ps1/start.cmd，独立虚拟环境安装时不依赖旧电商项目；当前电脑复用已有依赖减少重复下载。

## 10 最终本机验证
- 三套权重全部完成，固定revision、许可证和LFS SHA256记录在models/*/source.json，重新运行下载器验证通过。
- python verify_models.py：真实VideoMAE推理成功；6条声音样本均推理成功，原始分数写reports/model-smoke.json。因为与训练来源重叠，不称100%准确率。
- python verify_http.py：无音轨AVI画面成功/声音如实失败；带音轨MP4画面、声音、转写均成功；FLAC声音和转写成功；报告查询与删除通过。详情reports/http-qa.json。
- 重启亲安8010，健康接口video/audio/asr全部true，image=false。
- 删除已完成且已验证的三处models/*/chunks重复下载片段，路径均在本项目models内；保留完整权重及来源，不重复占用约1.76GB。
- reports/environment.json记录Python、PyTorch、Transformers、FastAPI、NumPy等实际版本。
- 没有启动新训练，没有把工程验证当成独立准确率。尚未验证中文老人语音、现代换脸/生成视频、真实诈骗识别效果。
