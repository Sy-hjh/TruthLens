# 文件与运行入口

## 平时使用

| 文件 | 用途 | 是否需要每天运行 |
|---|---|---|
| start-background.cmd | 双击启动后台服务并打开网页 | 推荐入口 |
| launch.ps1 / stop.ps1 | 后台启动/停止，只操作本项目进程 | 按需 |
| start.cmd | 终端前台启动，关闭窗口则停止 | 另一种入口 |
| run.py | Python服务入口，默认127.0.0.1:8010 | 开发时使用 |
| setup.ps1 | 换机器创建独立虚拟环境与依赖 | 仅首次 |
| requirements.txt | 通用依赖约束 | pip读取 |
| requirements-verified.txt | 本机实际验证过的核心版本 | 排查环境时参考 |
| requirements-dev.txt | 演示语音和技术PDF重建依赖 | 制作新演示时 |
| bootstrap.py | 项目缓存/临时目录、依赖路径与UTF-8配置 | 自动导入 |

## 业务代码

| 文件 | 用途 |
|---|---|
| backend/app.py | 上传校验、后台任务、API、话术规则、报告编排、转写校正、启动清理 |
| backend/detector.py | 独立图像/视频/声音分类、FFmpeg解码、分段声音、ASR回退 |
| backend/mandarin.py | 中文Paraformer本地转写，繁体转简体 |
| backend/tamper.py | TruFor局部编辑推理、真实异常矩阵PNG、权重安全加载 |
| backend/media.py | 视频时长校验与16帧采样 |
| backend/storage.py | SQLite报告增删查改 |
| backend/__init__.py | Python包标记 |
| frontend/index.html | 页面结构、上传、联系家人、练习、历史入口 |
| frontend/app.js | 上传轮询、报告、联系人、打印/导出、摘要音频与练习交互 |
| frontend/examples.js | 中文模拟材料入口与可纠正转写表单 |
| frontend/style.css / senior.css | 整体样式、大字触控与窄屏适配 |

## 下载、素材与验证

| 文件/目录 | 用途 |
|---|---|
| download_models.py | 下载固定到来源revision的图像、视频、声音、ASR权重；可传image/video/audio/asr_zh等单项 |
| install_trufor.py | 下载作者源码与官方权重，检查哈希；保留非营利许可证 |
| fetch_trufor_source.py | 本轮源码获取恢复辅助脚本；正常使用install_trufor.py |
| install_ffmpeg.py | FFmpeg发行包下载恢复辅助脚本 |
| download_samples.py | 下载6条英语声音工程样本，与训练来源重叠，不能当独立成绩 |
| download_chinese_samples.py | MINDS14中文真人电话语音小样本，记录出处和标签 |
| make_demo_audio.py | 通过微软通用TTS生成明确标注的虚构语音，不克隆真人；仅生成阶段联网 |
| models/*/source.json | 每项权重的来源、revision、哈希与许可信息 |
| models/asr_zh | 默认中文ASR；asr_small/asr是保留的Whisper回退 |
| vendor/TruFor | 作者原始推理源码与许可证；不是本项目原创算法 |
| data/demo | 三条中文模拟音频、四条摘要提醒及来源清单 |
| data/chinese-human | 私有本机评测副本，不随网页公开提供 |
| tests.py | 快速8项自动测试；隔离临时数据库 |
| verify_v2.py | 真权重功能断言；隔离报告与测试文件 |
| verify_http.py | 文件上传到报告与删除的HTTP全链路验证 |
| verify_models.py | 基础权重推理冒烟测试 |
| evaluate_manifest.py | 对有真实标签的独立清单计算分类指标；不是训练程序 |
| reports/*.json | 实际测试证据；user-*包含私人回归信息，已排除版本控制 |
| runtime | 日志、PID、缓存、SQLite报告及临时文件；不提交代码仓库 |

## 本轮新增：训练、复核、版本

| 文件 | 作用 |
|---|---|
| train_images.py | 用户原有图片分类头断点训练；冻结编码器，保留balanced-v1进度 |
| checkpoint_io.py / test_checkpoint_io.py | Windows文件占用时的安全保存、恢复与并发锁及测试 |
| training_status.py | 查看图片训练进度与验证结果 |
| prepare_training.py / prepare_recent.py / download_2026_pilot.py / download_balanced.py | 历史基础训练集准备、近年样本下载和类别平衡 |
| audit_dataset.py | 检查划分、哈希重复与生成器分组 |
| experiment_model.py / check_recent_model.py | 冻结图像编码器实验和ViT原始推理评测 |
| collect_domain_cases.py | 下载FraudBench；默认六类诊断集，--training下载其余类别训练集 |
| domain_model.py | 图像全局与四局部视角、JPEG增强、分类头结构和聚合 |
| prefill_domain_features.py | 缓存冻结图像特征，减少重复GPU计算 |
| train_domain.py | 商品分类头训练；线性或MLP，验证早停与断点恢复 |
| evaluate_domain_cases.py | 原图、压缩和TruFor三类商品诊断 |
| evaluate_domain_candidate.py | 商品新分类头的同条件复核；不会自动发布 |
| build_domain_gallery.py | 生成本地商品案例检查HTML，含真实模型结果与出处 |
| collect_news_cases.py | 下载新闻中报道的案例；无独立真伪标签，不参加准确率计算 |
| collect_ps_examples.py | 传统修图数据获取尝试；服务器失败，无成功成绩 |
| collect_video_examples.py | DeepSpeak公开样例下载尝试；TLS失败，不伪称已使用 |
| check_video_scenarios.py | 原视频模型18段初步换脸诊断 |
| install_face_detector.py | 固定commit安装并校验YuNet人脸定位模型 |
| backend/faces.py | 采样帧人脸定位、裁剪和无法定位时拒判；不识别人物身份 |
| train_video_head.py | 300段视频、冻结VideoMAE、人脸区域分类头训练，可恢复缓存和批次进度 |
| evaluate_video_release.py | 额外200段未参与训练的源视频复核，同时比较原模型；不训练 |
| install_integrity_v9.py / evaluate_integrity_v9.py | 下载校验及测试新局部修图候选，尚未启用 |
| install_audio_forensics.py | 固定commit下载2026 XLS-R/AASIST声音权重，safetensors安全装载 |
| prepare_audio_check.py | 60组中文真人/通用TTS同文本对照，不冒充人物克隆数据 |
| evaluate_audio_forensics.py | 新旧声音模型同一中文对照集测试 |
| backend/voice_forensics.py | 新声音模型的本地严格加载和分数映射，仅发布后启用 |
| backend/product.py | 商品专用模型的版本校验与推理，未达发布条件不开放 |
| backend/evidence.py | 汇总实际测试指标，避免把训练效果当业务准确率 |
| frontend/model-lab.html / model-lab.js | 浏览器查看各测试指标和当前模型版本 |
| range_stream.py | 有界内存、多段HTTP Range下载辅助，校验长度和响应 |
| stop_optimization.py | 为后台优化任务写停止标记；不能替代强制退出所有既有旧进程 |
| test_domain.py | 多视角/JPEG、场景校验、未发布时拒绝回退的自动测试 |
| vendor/audio_forensics | 审核后的作者架构，本地初始化改动明确标注，不隐式联网或回退pickle |
| vendor/integrity_v9 | 汽车局部编辑候选模型作者架构和预处理，研究保留 |

## 目录与当前说明

- `现在只看这份.md`：唯一当前使用入口、模型结果与训练命令。
- `docs/CONTINUATION.md`：每轮做法、选择、失败与修复过程。
- `docs/THIRD_PARTY.md`：模型、数据、算法出处和许可限制。
- `models`：基础权重、实验训练结果和显式启用版本；不删除旧训练。
- `data`：按用途分开的训练/验证/测试/诊断素材；不是网页公开目录。
- `runtime`：日志、断点辅助缓存与本地报告数据库；不打进参赛源码包。
- `reports`：原始实验结果。私人user-*回归资料不打包。

不要凭训练轮数判断完成。达到某轮后，应比较未参与训练的真实误报、合成漏检及压缩条件表现。实验模型不会因为训练结束就自动替换网页模型。

## 3.0当前文件补充

| 文件 | 用途 |
|---|---|
| team.json | 团队提供的真实学校、成员与指导老师；队名为亲安守望队，不虚构分工 |
| web/src/main.tsx | React入口、导航、错误边界与视图懒加载 |
| web/src/api.ts | 类型定义、请求错误处理和报告导出 |
| web/src/views/Upload.tsx | 文件预览、上传、任务轮询及刷新恢复；公开模拟按钮 |
| web/src/views/Report.tsx | 分项模型证据、局部热图、转写校正、资料解释与导出 |
| web/src/views/Contacts.tsx | 当前浏览器的预留联系人和tel链接，不传入模型 |
| web/src/views/Practice.tsx | 四类核实情景练习 |
| web/src/views/History.tsx | 报告检索、查看与删除 |
| web/src/views/Evidence.tsx | 真实误报、漏检、样本数和启用版本 |
| web/package-lock.json | 已验证前端依赖锁；npm ci按此恢复 |
| frontend-next | 生产构建结果，日常启动直接使用；frontend保留此前版本源码 |
| backend/knowledge.py | 小型审核资料库、BM25检索、来源链接与核实动作 |
| backend/advisor.py | 本地Qwen3结构化建议选择、引用校验与检索兜底 |
| backend/sifta.py | 作者等效X-CLIP短片段采样与人脸推理，拒绝无可用人脸 |
| backend/video_fusion.py / video_math.py | 两个冻结时序模型及校准分数，只对画面，不融合成诈骗概率 |
| calibrate_sifta.py | 单模型验证集阈值实验，未自动替换网页 |
| calibrate_video_fusion.py | 在旧验证来源组拟合双模型非负校准层，拟合成绩不当独立测试 |
| collect_video_final.py | 排除先前来源组后，下载100来源、300段最终复核材料 |
| evaluate_video_final.py | 固定模型与阈值的新来源复核，可保留中间进度 |
| install_siglip_face.py / evaluate_siglip_face.py | 失败的人脸帧候选实验，非日常运行入口 |
| install_advisor.py | 固定版本本地解释模型安装，可续传并验证SHA256 |
| verify_delivery.py | 隔离数据库中的真实模型上传、报告、错误与清理验收 |
| test_advisor.py | 检索、动作越权、引用伪造与API约束测试 |
| build_submission_pdf.py | 从真实指标和team.json重建技术PDF |
| install_release.py | 换机恢复审核版本；不下载训练全集 |
| release/release.json / video-head.pt | 固定启用配置、来源与训练分类头；不含私人样本 |
| stop.cmd | 双击停止本项目后台服务 |

日常只启动网站；以上实验、训练和下载程序按需要使用，不要为了打开网站全部运行一遍。
## 新增交付辅助入口

- verify_deployment.py：真实8010服务的资源、上传、版本与删除核对，创建的公开测试记录随后删除。
- export_public_evidence.py：导出不含私人素材与转写的真实指标摘要，便于源码包实测页复查。
- build_source_package.py：打包源码、构建、固定分类头与公开摘要，自动检查不包含私人媒体和数据库。
- docs/history：以前的训练阶段说明，按当时事实保留；当前以根目录《现在只看这份.md》为准。
