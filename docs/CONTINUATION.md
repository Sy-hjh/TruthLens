# 2026-11-10 继续完善

用户要求完整、测试充分的版本；不再将主流程能运行视为全部完成。

## 原图回归
- 根据旧报告的文件名和SHA256，定位原先两张原图；仅做本机推理，没有上传第三方，也没有拿它们训练。
- 新候选Ateeqq/SigLIP对真人图给出AI分数0.00138，对用户标注AI图给出0.000689，仍漏检。
- 结果原样写reports/user-regression.json，不调分数掩盖失败。
- 正在加入独立局部篡改模型，因为整图生成检测不能代替局部编辑检测。这只是技术路线，不提前保证能检出原图。

## TruFor
- 作者代码固定commit ae54475df6f41a491d7615100feb19263dec13f7，放vendor/TruFor，保留原始版权与许可证。
- 官方许可允许信息、非营利用途，禁止未经授权的营利使用。当前教育研究演示按此范围使用，不宣称商业授权。
- git clone失败、codeload断流；改为按Git树下载推理源码，空文件直接建立，已有文件用Git blob SHA1检查。
- 官方权重按4MiB范围请求下载，按作者给出的MD5验证；不使用未知镜像。
- 本地适配器保留作者RGB/256预处理和strict权重加载；最大长边1024以控制8GB显存，报告记录缩放。
- 仅展示真实模型异常矩阵，不使用压缩误差图冒充篡改定位。

## 中文材料与识别
- SAPI本地语音不可用后，使用edge-tts通用中文声音制作三条明确模拟音频和四条摘要提醒。没有克隆真实家人，检测阶段无需把音频传给外部服务。
- HF datasets-server多次502/503，改为按固定revision下载MINDS14中文parquet，验证SHA256，再提取前6条真实电话语音。
- 英语训练声音检测器在6条中文真人上，0.5阈值误报2条；原样保留reports/chinese-human-pilot.json，不调阈值后冒充独立成绩。页面加入较强/不明确/未明显检出的展示，显示区间未经领域校准。
- Whisper-small与中文Paraformer在相同85参考字小样本比较，字符错误23与5，选择Paraformer为默认，Whisper保留回退。只证明这批样本，不外推老人方言准确率。
- 支持人工纠正，保留原始转写、校正记录及模型分数。文字规则支持简繁转换与部分否定表达，仍是透明规则而非通用语义识别。

## 图像与安全
- TruFor对用户实拍/标注AI原图输出0.291/0.599，记录私人回归；整图模型两图均漏检。没有把小样本转成准确率。
- 热图由真实异常矩阵生成，标注亮处不等于已证实修改。
- 临时文件清理完成、报告保存后才将任务标为完成；启动时清理限定目录，避免中断遗留原图。
- 摘要用项目本地音频；修正提醒为“先不要转账，也不要提供验证码”。

## 本轮运行与验收
- python tests.py：8项通过；python verify_v2.py：8种真权重功能输入全部符合断言；python verify_http.py：无音轨视频、有音轨视频、FLAC上传报告和删除通过。
- 损坏PNG、静音与181秒视频的报错是有意负例，保留日志；没有掩盖成成功。
- 浏览器实测中文演示、用户原图上传、联系人刷新保存和tel链接、390像素布局。测试联系人已移除，未拨出电话。
- 增加launch.ps1/stop.ps1/start-background.cmd，避免聊天结束后前台工具会话退出导致网页断开；保留日志和PID并检查进程归属。
- 补齐FILES、ACCEPTANCE，重写当前README、DELIVERY、DEMO，旧日志保留历史事实。
- 调研DeepSpeak与SWAN-DF：官方数据需要申请/协议，未绕过授权下载或拿无标签网络视频充当独立测试。没有新训练；用户明确不需要改成全参数微调。

## 最终复测补充
- 捕获普通工具会话启动的服务退出问题后，使用独立隐藏进程启动；没有修改防火墙或公开监听。随后stop.ps1/launch.ps1实际停止重启成功，health版本2.0.0，六模块全部true。
- 浏览器实际校正普通对照的标点并保存，模型93.6/99.1原始分数保持不变，规则无命中。导出JSON成功，摘要音频readyState=4无媒体错误。
- 手机报告截图保存reports/ui-mobile.jpg；该次窗口innerWidth423、内容408，无横向溢出。早先390像素也检查通过，结束前恢复默认视口并保留网站标签。
- Python代码用Black25.1.0格式化，前端用Prettier3.6.2格式化；8项自动测试复测通过，Python编译检查和两份JavaScript语法检查通过。
- 下载器修正为固定本次验证revision，避免未来main变化造成配置/来源混用；实际运行asr_zh下载校验成功，没有重新下载完整权重。
- 中文ASR失败时允许Whisper-small独立回退，不要求必须同时安装tiny。新增DATASETS说明数据集和模型不是同一概念，以及本地子集实际体积。
- 验收汇总保存在reports/acceptance-summary.json。未进行实际拨号，未上传私人原图到外部，未运行新训练。

## 用户要求效果优先与手动续训（2026-11-10）
- 官方资料：Community Forensics（CVPR2025）、AIGenImages2026（MAD2026），不是把旧CIFAKE换名。新权重86,678,644字节，revision26afc31e6b40c312c3fd42c05a758be62446215b，下载SHA验证。
- HF小版全量278GB不适合先试，rows可以返回生成图；filter真人数据反复500，记录失败后改用COCO8八张实拍作为流程对照，来源差异明确保留，不将17/17宣称独立准确率。
- 2026数据官方viewer不可用；改tar.gz流式读取前20张，仅用extractfile读字节，按SHA命名，不执行档案路径，下载28,103,450字节图像，未下载11GB全包。文件名可见GPT Image1.5/Gemini/FLUX。原始档案train，另行本地实验划分。
- 2025新模型遵循作者Resize短边256/CenterCrop224/ImageNet归一化/单logit sigmoid。初次采用方形Resize后已核对作者代码纠正，正式2026报告用正确预处理。
- 原图2张新模型仍漏AI；2026的20张只检出9张、漏11张。与新生成器分布变化一致，但不能用小样本下总体结论。
- 新增train_images/experiment_model：冻结编码器、训练头，按类别加权，保存AdamW状态、总步数、epoch与样本位置。每批临时文件原子替换last.pt；Ctrl+C/SIGBREAK完成当前更新后保存，STOP文件也能请求停止。加载用weights_only=True。训练全程本地不调用LLM。
- 最终37张：train25/val6/test6。模型/数据源分组并非严格隔离，只是工程和小规模探索，不宣称领域准确率。原图私人回归绝不进入训练。
- 实际暂停1步后续训到2轮共14步。6张留出测试前后均对5张，未证明提升；不替换网站权重。独立与连续训练权重比较结果见reports/training-resume.json。
- 给用户单一中文操作入口《先看这里_手动训练.md》，把复杂记录留在后面供复现。新训练仅针对整图AI生成，不把它说成视频/声音训练完成。

## 十轮后扩充数据与训练判断
- 读取用户真实history：1至10轮均balanced_accuracy=.75，correct=[2,2]/total=[2,4]。不是系统准确率75%，普通准确率4/6，没有改善证据。
- C盘起始剩104,789,049,344字节。配置至少60GiB才启动，保留50GiB，目标真假各2000张，不盲目下载278GB全量。
- AIGenImages2026流式取前2000张，包含19类生成器；共3,543,350,649字节。普通单连接慢，改有限16并发4MiB Range前读，有界缓存，不下载11GB整包；中断后图片保留，但gzip要重读前缀，未宣称字节级续传。
- COCO原域HTTPS证书主机名不匹配，没有关闭证书验证。改作者图片桶的有效S3 HTTPS路径，读取官方image_info_test2017.zip，从官方test2017取得2000张真实照片，保留元信息与许可列表。
- 原图真实内容哈希无重复。根据UUID/数字后缀解析生成器，Firefly提示词文件统一归Adobe-Firefly；最后使用更新后的分组逻辑从缓存重建。新train2734、val632、test634，真假配平，AI生成器本地不交叉；不宣称基础模型预训练完全独立，COCO源偏差保留。
- 图片占用3,872,586,191字节，最终校验全部哈希与集合，report=balanced-data-audit.json，校验时C盘剩97,691,508,736字节。没有覆盖旧十轮。
- train_images新增val_loss、真人误报率/AI漏检率、验证连续不改善patience，checkpoint保留计数；默认旧参数仍可恢复。最好模型按平衡准确率、同分验证损失选择。新增train_balanced.cmd，20轮上限、patience5，用户手动跑。
- 新数据真实模型训练第1批后重启，从step1恢复到step2，共8张处理，使用隔离balanced-smoke。验证与训练必须同时包含两类、同文件不能跨训练验证。指标函数用已知混淆矩阵断言通过；中文摘要training_status实测读取十轮。
- 操作和阶段目标统一放《十轮之后看这里.md》。建议阶段目标90%平衡准确率/FPR<=5%/FNR<=15%只是假设验收目标，不是现有成绩或行业认证，不以轮数承诺准确率；最终测试保留不用于逐轮调参。
`n- 公开基础模型在632张新验证集起点：平衡准确率65.35%，真人4/316误报，AI215/316漏检。不是旧十轮模型的同集对比，也不是新数据训练后成绩。634张最终测试未运行。完成后确认旧history仍为10轮，新数据save/resume为step2/cursor8。大数据目录加入gitignore，避免误提交数GB图片。
2026-11-10 保存锁定修复：用户WinError5发生在last.tmp替换last.pt；只读确认主文件step2048/cursor2720，临时文件step2049/cursor2724均可读。新增checkpoint_io：重试原子替换、持久锁定保留唯一完整恢复文件、读取最新有效主/旧临时/恢复文件、输出目录进程互斥。模拟短暂占用、持续占用/遗留恢复、双进程锁三测试通过。隔离runtime/recovery-check验证，原始用户检查点未改动。

## 20轮完成后的评测
# 训练结束：本次结果

训练完成20轮，验证选出的最佳是第18轮，不是最后一轮。使用models/balanced-v1/best/model.safetensors。

| 指标 | 验证集632张 | 留出测试634张 |
|---|---:|---:|
| 平衡准确率 | 94.62% | 98.11% |
| 真人误报率 | 4.43% | 3.15% |
| AI漏检率 | 6.33% | 0.63% |

测试真人317张，误报10；AI 317张，漏检2。这是本数据范围的成绩，不是任意GPT/老人/电商图片准确率。634张测试在选好模型后运行，不能再据此反复调参数又当成全新独立测试。

## 用户原图回归

你的两张原图本轮预测符合标签0/2。它们没有进入训练，不拿两张结果算领域准确率。具体私人路径与分数保留在reports/user-balanced-trained.json。

## 接下来

先不要继续机械追加轮数。best是本轮候选，last.pt是续训状态，两者用途不同。网站当前没有自动换权重。接入前还要检查压缩/截图、更多授权实拍与新生成素材，并独立验收视频、声音、P图定位；不能把本次整图实验扩展成所有功能的成绩。

如果改变模型或阈值，需要用验证集选择，再另留新测试数据确认。保留本次模型及记录作比较，不覆盖已有成功实验。

详细逐张和生成器分组结果：reports/balanced-test.json。权重与清单哈希：reports/trained-model-selection.json。原始模型在相同验证集的平衡准确率为65.35%，本轮最佳为94.62%，这说明在该验证集上有提升。


## 用户授权代收集实物/生成/编辑材料
# 这次商品场景检查，看这一份

材料已经替你收集和整理，不用自己凑图。本次是找出场景问题，不是继续堆训练轮数。

## 收集了什么

- 30张作者标注的正常商品买家图。
- 30张作者标注的真实破损商品买家图。
- 180张AI修改图：前面30个正常商品案例，每个有6种生成模型的版本。
- 4张商家遭遇疑似AI售后的新闻案例，真假未独立核实，不计准确率、不用于训练。
- 覆盖家居厨具、电子、食品、服饰、运动和玩具，240张商品原图约438.5MB。来源为2026 FraudBench，CC-BY-NC-SA-4.0；版权与作者标签保留，不宣称比赛自动豁免许可。60张真实图的真实性依据来自作者数据分类，不是我们亲自拍摄或独立鉴定。

## 结果

| 检查 | 样本 | 真人误报 | AI修改漏检 | 平衡准确率 |
|---|---:|---:|---:|---:|
| 你的整图模型 | 240 | 9/60（15.00%） | 76/180（42.22%） | 71.39% |
| 同图JPEG60压缩 | 240 | 0/60（0.00%） | 164/180（91.11%） | 54.44% |
| TruFor局部模型抽测 | 60 | 4/30（13.33%） | 26/30（86.67%） | 50.00% |

整图生成检测与局部编辑检测是不同任务，上表是把它们放到本批“商品AI改图”场景做压力测试，不说明谁能通吃所有图片。样本来自30个原始正常案例，6种版本互相关联，不能按180个完全独立案例理解。TruFor只抽测30真/30改图，不与整图240张的总分直接排名。

## 怎么看图片

双击项目根目录的 **商品案例检查.html**，不用启动服务器、无需联网，能按真实正常/真实破损/AI改图/新闻筛选，查看原始分数、压缩后分数、部分真实模型异常图与来源链接。缩略图仅查看，检测使用下载原文件。

## 我做过哪些验证

240张商品文件SHA均唯一，与旧4000张没有字节完全相同的素材。冻结了你当前best的副本，模型哈希记录在reports/domain-evaluation.json，避免训练过程中更换权重影响对比。新闻图片没有强行贴真/假标签。全部评测在本机进行，没有把你原图传给第三方，没有改网站权重，也没有把这些检查图加入训练。

豆包应用已检查，显示Seedream5.0Flash可用；本次找到现成、多生成器且带来源记录的商品案例，所以没有额外消费豆包生成次数，也没有调用WorkBuddy代写或更改项目。

## 当前没有冒充完成的部分

这180张是AI编辑/生成式破损材料，不冒充传统Photoshop手工拼接数据。传统PS补充下载尝试遇数据服务500，未取得可用样本，不算入上述数量。MVTec、CASIA、COVERAGE的调研和失败保留工程记录，没有拿无标签图补齐数量。

本次不凭公开新闻就指控具体买家造假，不将数据集中的“真实破损”误当成AI造假。下一轮若需要做场景训练，应另外取新材料，按原始商品/评价组隔离，不能把这批测过的图练过后又作为全新独立测试。

## 文件在哪里

- data/domain-cases：240张商品原图、30份编辑记录、来源清单。
- data/news-cases：4张新闻例图及来源，标签为空。
- reports/domain-results.csv：中文列名的逐张结果，可用Excel打开。
- reports/domain-evaluation.json：详细数据与模型哈希。
- reports/domain-heatmaps：少量真实模型预测异常图，不是人工真实修改掩码。
- collect_domain_cases.py / collect_news_cases.py：可重复的收集入口，已下载文件会复用。
- evaluate_domain_cases.py：独立场景检查，不训练、不替换网站。
- build_domain_gallery.py：生成离线检查册。

来源：https://huggingface.co/datasets/TristanYan/FraudBench 、https://github.com/Tristan0318/FraudBench 、https://m.voc.com.cn/xhn/news/202508/30206702.html 。

下载一度连接重置，保留已下文件、并发从12降4后完成；未关闭TLS校验。HF固定revision=27d94c1a4c4b087845f8a8e916473cdd6a5c6011。
浏览器验收：离线检查册全部244张、真实破损筛选30张、AI改图筛选180张，原图/压缩/局部分数已显示；截图reports/domain-gallery.jpg。临时预览仅提供runtime/domain-preview下的自包含HTML，验收后关闭浏览器测试标签并停止8011预览服务，最终文件无需服务器。全部240张来源哈希再次核验，240整图/压缩结果和60局部结果完整。

## 2026-11-10 持续优化：从诊断进入训练与独立复核

用户明确要求继续把项目做成可演示、可测试、可交付的系统，本轮没有再把下载清单当成交付结果。

1. 商品训练补充：从 FraudBench 其余23个类别下载551张图片（约944 MB），与此前六类240张诊断图片按类别隔离；训练前剔除跨集合字节重复及其来源组。冻结 ViT 编码器，训练整图+四个局部视角分类头，使用原图、JPEG60、JPEG85。线性头与MLP头均已训练完成。MLP在诊断集JPEG60平衡准确率69.72%，优于原先54.44%，但真实图片误报25%，所以没有启用商品专用模型。旧诊断集已被观察，不能再称为完全未见的最终测试集。
2. 局部编辑模型复核：下载并审核 car-damage-photo-integrity-v9 的本地代码，权重117,750,936字节，固定commit并校验SHA256。使用作者upload预处理（长边1600/JPEG85），固定作者原阈值4.193077，不把原始logit当概率。在60张商品诊断图上真实误报0/30、AI漏检22/30，平衡准确率63.33%。这是汽车领域模型的迁移诊断，尚不足以替代现有模型。
3. 视频训练：下载 RTFS-10K 300段短视频（约380 MB），150个不同源YouTube ID。100来源训练、25验证、25测试，每来源真实/换脸各一段；训练验证用inswapper，测试用uniface。身份没有人工核实，不声称人物身份隔离。先提取人脸区域，冻结 VideoMAE，只训练分类头。全部300段可定位人脸，无拒判。按验证集选择最佳分类头，50段测试判对45段，真实误报3/25、换脸漏检2/25。独立追加另100个源ID的200段复核正在进行；不据50段测试承诺泛化90%。
4. 人脸定位使用OpenCV Zoo YuNet，固定commit、LFS SHA256和MIT许可。仅定位，不进行人脸身份匹配。少于半数采样帧检出人脸时拒绝给该模块结论。
5. 声音方面发现CFSDD、RTCFake、QuadVoxBench和Qwen3合成语音数据集均需人工审核申请；没有接受协议、伪填身份或绕过下载。改为审核2026 Forensics XLS-R/AASIST公开模型，优先safetensors，移除作者推理中的隐式下载及pickle回退，直接从本地配置初始化并严格装载全部权重。正在下载与测试，不写成已经接入。
6. 建立60组中文内容匹配诊断：公开Minds14真人电话语音与三种明确标注的通用Edge TTS声音，文本一致。不是特定人物克隆，不作为最新克隆攻击基准；公开来源可能与预训练重合，人物分组未知，完整记录这一限制。
7. 网页新增“实测与模型版本”只读页，分数据集展示误报漏报，不拿旧来源留出集98.1%宣传通用能力。加入场景模型权重哈希校验和显式版本文件；没有发布文件就不启用。商品入口未达标时不对老人展示不可用选项。
8. 修改后12项API与领域模型检查通过，前端JavaScript语法检查通过。最终真权重端到端和浏览器复测将在模型复核后完成。

执行入口：train_domain.py、train_video_head.py、evaluate_video_release.py、install_integrity_v9.py、evaluate_integrity_v9.py、install_audio_forensics.py、prepare_audio_check.py、evaluate_audio_forensics.py。数据、缓存和用户历史进度分别保存，不覆盖用户balanced-v1训练结果。

## 2026-11-11 交付候选版与用户复核

- 用户要求继续全部工作，但先不录演示视频，先把网站和其他材料准备好，由用户检查。已遵从，没有生成演示视频、没有公开仓库或提交比赛。
- 团队信息按用户提供写入team.json：亲安守望队（本次拟定），大连东软信息学院，胡瑾慧、周宇航、陈浩翔，指导老师李予诺。未虚构成员分工。
- 中断后的Qwen3与SigLIP人脸候选下载从已完成字节续传，最终SHA256验证通过。SigLIP在50段验证集平衡准确率56%、200段诊断59%，未接入。
- 固定两套冻结时序检测器，在原验证来源组拟合非负L2校准层；系数约[0.48050,0.59098,0.00033]，阈值0.5。没有用最终新测试组调整系数或阈值。
- 新增100个未参与本地训练/校准/此前诊断的源ID，真实、inswapper、uniface各100段；检查源ID及字节哈希无重叠。300段全部可处理，真实误报5/100、换脸漏检55/200，平衡准确率83.75%、普通准确率80%。不声称人物身份隔离或所有生成器准确率。
- 将分类头复制为不可变哈希版本，网站配置固定qinan-video-fusion-r1-20261111；保留原始用户训练目录。加入分类头和基础编码器校验。
- 60组中文真人/同文本通用TTS对照，新声音模型真实误报0/60、合成漏检3/60；旧模型真实误报18/60。新声音版本固定启用；它不是最新声音克隆或老人场景基准。
- 本地Qwen3实际运行成功，受限动作与引用校验通过；无云端API、无联系人读取、无转账/拨号/外发工具。知识库为审核的小型公开资料集合，没有包装成完整知识库或无限自主Agent。
- React/TypeScript/Vite生产构建通过。已补页面刷新恢复任务、数据库恢复已完成报告、最近100个任务内存限制、删除报告同时清除内存副本、打印时展开技术依据。
- 自动检查23项通过。8份材料的真实权重上传/报告/删除/清理流程通过，包含损坏图片和静音的预期失败。真实TCP8010上传已经验证served版本，后续新增公开对照2再次核验。
- 公开演示按旧50段测试报告来源顺序选前三组，不按分数挑选。第一组换脸被实际漏检（约0.336），保留且明确标为漏检回归；第二/三组换脸约0.689/0.610，原视频约0.087/0.108。没有根据标签伪造分数。
- 浏览器此前核对了正式比赛规则及React窄屏首页、练习反馈。尝试桌面浏览器时，Windows工具无法可靠确认当前网址而停止了Computer Use；未绕过该检查、未继续窗口输入。构建、真实模型和API测试继续完成，桌面外观、打印和手机拨号由用户复核，不写成全平台自动通过。
- 技术PDF为8页，采用真实团队信息、实际指标、架构、出处和边界，已渲染逐页检查布局。当前入口统一为《现在只看这份.md》，包含启动、截图位置、训练、版本和实际验收范围。

### 最终运行服务补充检查

- 最后一次实际TCP上传使用按顺序选定的案例2换脸，服务返回固定qinan-video-fusion-r1-20261111，分数约0.689，达到该模型0.5核验阈值；不是只检查离线脚本。
- 已通过运行服务POST /api/cases/{id}/advice，实际执行本地Qwen3检索增强工作流，返回合法来源和枚举动作，原视频分数未被解释助手修改；仅删除自己创建的工程记录。
- 已生成本地可审阅源码包，排除私人媒体、联系人、历史数据库、大型预训练权重及node_modules，并检查ZIP结构和CRC。提供固定分类头及换机恢复脚本。
- Git记录从本次候选交付真实建立，旧阶段保留日志，没有伪造历史提交。尚未向外部仓库推送。

## 最新文字训练限制
新增ScamGen字符分类器12轮：82,090训练、7,026验证、7,486测试，五类70.44%；BERT冻结语义12,000训练65.01%候选未上线。高阈值仅作实验提醒，测试非诈骗误提醒4.83%、诈骗召回10.86%，不能伪装高准确率或直接判诈骗。下一步需更广的普通聊天负例、按案例/模板隔离的现代中文套路标签、冻结语义特征更合适的分类头和全新外部截图测试；不得用当前测试继续调参数后仍称独立测试。所有已看到的测试必须标成后续对比。论文和语音稳定性详见本轮说明。

## 最新区域/时序实验
160张同图比较：现用3图块验证FP0/FN9，测试FP0/FN2；九宫格或整图+九宫格验证FP3/FN15、测试FP0/FN4，未上线。真实FTCN32连续帧36条：FP0/FN15、BA68.75%，同组GenD FP2/FN0、BA91.67%，均为已观察数据后续诊断。FTCN来源2021，不是最新；2025FakeSTormer公开权重ZIP约1.98GB未完成下载，部分8MB在models/fakestormer。时序、口型同步可靠上线仍未完成，不能宣传。图片新增sampling真实坐标，后端41项检查通过。

## 11月12日覆盖上述历史状态

FakeSTormer完整下载且已跑通，但同组新60段较差。OmniAID2026完整权重已测，新增Mirage240测试Smaug93.33%、Omni78.75%，保留Smaug。真正本地训练有序GRU头已经完成并上线：冻结GenD编码器，四帧共同输入（从32帧范围取0/10/21/31，最多4段），训练23轮选13轮；新60段FP2/20、FN2/40、BA92.5%，同组旧八帧BA83.75%。未知上游/人物重叠，不是全生成视频或口型同步。旧300/180段已退役作此头训练/验证，不再用旧成绩证明此头泛化。

active-video为video-ordered-head，版本qinan-ordered-gru-r1-20261112。release/ordered-video-head.pt和protocol已纳入源码包恢复流程，源代码字节SHA受校验，train_temporal_sequence.py和fakestormer_candidate.py固定LF，改这两文件应创建新版本/新测试，不能绕过校验。原GenD配置备份models/video-before-ordered.json。训练入口及数据/权重/来源/失败记录统一见docs/本轮模型升级与复现.md。实际HTTP和浏览器图表已通过，当前服务8010在运行，未录制视频。保持如实限制，不能宣称完美或全模态90%。

## 最新：截图风险与带声音画样例

backend/chat_assessment.py根据逐字原话的要求组合显示疑似提醒，附真实公安案例；旧70%实验分类器收进研究记录，不覆盖已提取风险。新消息原文提取不可用时，有限匹配明示rules_only。聊天的普通借款/否定/教育反例有测试。资料为汕尾公安2023-05-26历史案，不能改称今日新闻。

八个素材05–08已换FakeAVCeleb作者公开A/D原片与抽取音轨，A真人原声＋真画面，D克隆声＋假画面。2021英语示例，只作功能对照；新四象限A/B/C/D音画分别真实检测正确，不是独立通用准确率。主页新增av-real/av-fake带声入口，prepare_av_demos.py按作者公开链接及SHA恢复，release恢复已接入。旧中文音频和静音片备份data/demo-revisions/20261112-v1。过程详见docs/八个演示素材修正说明.md。截图01/02、音频05/06及所有AV输出已核验，浏览器chat-risk-case-v2-browser.png和av-dual-signal-v2-browser.png是实际新UI。不要把旧八素材单模块通过报告当作新版完整验收。


## 2026-11-13：用户授权增加音视频双检查

原合成检测保留，音视频新增独立ASR→内容风险；新字段transcript/speech_analysis，speech-text校正仅更新文字分析、不改变modules。原/transcript保持退休。ASR/内容失败独立隔离，静音不造文本；保存转写需在报告明确提示可历史删除。使用已安装Paraformer/Whisper和本地Qwen，没有新训练或调低合成阈值。

实际HTTP三组通过：虚构中文借款TTS触发疑似熟人借款；普通内容合成声未触发内容警告；作者真人带声视频完成画面/声学/转写内容，校正前后modules完全一致。普通对照初次因“验证码”名词误报，保留失败日志，修正为需操作要求证据后重测通过。52项后端检查、网页构建通过；浏览器speech-dual-browser.png实际显示转写内容、原话及风险。不是增加了就保证总体准确率更高，绝不合成诈骗概率。

新文件backend/speech_content.py、web/src/views/SpeechContent.tsx、test_speech_content.py、verify_speech_dual.py；详见docs/音视频双检查说明.md。Claude交接新增根目录语音双检查增补，原包及带“含语音双检查”版本均更新参考源码；需提醒用户转交增补，旧版不转写需求已被本次授权替代。未制作实时录屏，未录演示视频，未发布公网。


## 2026-11-14 有声视频与提速
详见 2026-11-14_音轨故障与速度优化.md。实际完整三项冷启动51.7秒、热启动19.2秒；58项测试通过，浏览器公开带声伪造对照通过。未停止用户其他训练。


## 2026-11-14 按评分升级后端（前端禁止修改）
采用LangChain1.5.0/core1.8.0/LangGraph1.2.21，依赖隔离.agent-packages；本地Qwen原生工具调用，报告/混合检索/来源核对工具；选择引用后程序绑定审核动作，保留失败兜底。新增SSE、反馈、审计与删除联动。原检测权重阈值和训练未变、前端目录零差异。70项回归通过，真实Agent三场景通过，公开有声视频完整HTTP+SSE+反馈删除闭环通过。失败工具格式与引用配错日志仍在runtime。入口docs/评分标准逐项对照_20261114.md；源码包与接口增补同步。尚缺前端流式展示、手机性能/适老可用性、独立泛化和商业试点；不能承诺全部满分。


## 2026-11-14 TruthLens frontend integration delivered
- Reimplemented ZIP design inputs within React/strict TypeScript. Warm hero, lime/purple system, lazy Three lens, accessible dialogs, responsive navigation and reduced motion.
- Real upload/polling, batch keepalive, module charts, streamed LangChain report questions and citations, feedback, local trusted contacts, practice and history. Removed developer-facing demos; exact recorded fixture hashes used to reversibly hide QA history.
- Security/cache/gzip verified by HTTP. Selected video stack lazy import preserved exact score. Memory budget closes only own idle voice/text caches, never running inference or user training.
- Validation: 79 backend tests; 6 Node cases including 9 threshold assertions; strict TS, formatting, production build; 8 old curated media regressions pass; 2 prior user-labelled image regressions pass (private images excluded). Not general accuracy.
- Browser: 320/390/768/1440 layout, quiz feedback, contacts validation/cancel, report export, actual Agent citations, unsupported-file error and navigation during upload checked. Earlier low RAM caused slow browser observation; preserved in limitations. Final cold audio/video paths took roughly60-103s, not a universal latency guarantee.
- Deliverables: new TruthLens docs, actual screenshots, source ZIP and public validation summary. No demo video recorded. Real elderly trial and physical-device evidence pending, task sheet supplied. Conservative rubric estimate83-92, not full marks.


## 2026-11-14 Motion edition
Canvas constellation with pointer repulsion/ripples, aurora, Three orbit satellites, title/CTA light, staggered reveal, card tilt/orbits, reading progress. No model/threshold/API change. Strict TS/build and 6 Node cases passed. Browser1440/390, reduced motion, mobile menu/workbench checked. Fixed negative ripple radius on immediate resize; fresh-page console clean. See TruthLens_动效升级说明.md.


## 2026-11-14 Full-site observatory + companion
Added page-specific interactive observatories, orbit angle/expand/pause controls, roaming/draggable vector companion, real local Qwen platform RAG API and existing report-agent mode. No fine-tuning performed or claimed; no detector changes. 87 backend tests pass;6 Node cases and TS build pass. Real local model answered3 topics;final HTTP payment question41.88s mode local_qwen_rag with explicit program-bound callback steps. Fixed mobile overflow:hidden internal focus-scroll displacement using clip. See TruthLens_全站交互与小鉴助手.md.
