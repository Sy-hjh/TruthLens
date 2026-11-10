"""Rebuild contest PDF from actual metrics and team.json; never invent test results."""
import bootstrap,json,html
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing,Rect,String,Line,Polygon
ROOT=bootstrap.ROOT;OUT=ROOT/'submission';OUT.mkdir(exist_ok=True)
pdfmetrics.registerFont(TTFont('CN','C:/Windows/Fonts/simhei.ttf'))
GREEN=colors.HexColor('#173f35');LIGHT=colors.HexColor('#eef3e5');GRAY=colors.HexColor('#6d7b70')
styles={k:ParagraphStyle(k,fontName='CN',fontSize=size,leading=leading,textColor=GREEN if k!='small' else GRAY,spaceAfter=gap,wordWrap='CJK') for k,size,leading,gap in [('title',29,41,22),('h1',20,28,20),('h2',14,21,12),('body',11,18,12),('small',8.5,14,9)]}
def P(text,kind='body'):return Paragraph(text,styles[kind])
def metric(file,key='metrics'):
 p=ROOT/'reports'/file
 if not p.exists():d=json.loads((ROOT/'docs/benchmarks.json').read_text(encoding='utf-8'))['reports'][file]
 else:d=json.loads(p.read_text(encoding='utf-8'))
 return d[key] if key else d

def pct(x):return '—' if x is None else f'{100*x:.1f}%'
def table(rows,widths=None):
 cells=[[P(html.escape(str(c)),'small') for c in row] for row in rows];t=Table(cells,colWidths=widths or [140,75,75,90,90],repeatRows=1,hAlign='LEFT');t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),LIGHT),('LINEBELOW',(0,0),(-1,0),.7,GREEN),('LINEBELOW',(0,1),(-1,-1),.3,colors.HexColor('#dce4d5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),9)]));return t

def architecture():
 d=Drawing(500,260)
 nodes=[(5,195,490,48,'React + TypeScript网页：上传、报告、家人联系、练习'),(5,117,490,48,'FastAPI任务编排：文件校验、独立检测、清理、记录'),(5,35,153,50,'视频 / 声音 / 图像模型'),(174,35,152,50,'本地中文语音转写'),(342,35,153,50,'检索资料 + Qwen3解释')]
 for x,y,w,h,label in nodes:d.add(Rect(x,y,w,h,rx=7,ry=7,fillColor=LIGHT,strokeColor=colors.HexColor('#b8c9ab')));d.add(String(x+w/2,y+h/2-4,label,fontName='CN',fontSize=10,textAnchor='middle',fillColor=GREEN))
 for x1,y1,x2,y2 in [(250,195,250,165),(250,117,82,85),(250,117,250,85),(250,117,418,85)]:d.add(Line(x1,y1,x2,y2,strokeColor=GRAY));d.add(Polygon([x2-3,y2+6,x2,y2,x2+3,y2+6],fillColor=GRAY,strokeColor=GRAY))
 return d

def main():
 team=json.loads((ROOT/'team.json').read_text(encoding='utf-8'));audio=metric('audio-mandarin-check.json');video=metric('video-final-evaluation.json');vd=metric('video-final-evaluation.json',None);accept_path=ROOT/'reports/delivery-verification.json';accept=json.loads((accept_path if accept_path.exists() else ROOT/'docs/acceptance-evidence.json').read_text(encoding='utf-8'));release_path=ROOT/'models/active-video.json';release=json.loads(release_path.read_text()) if release_path.exists() else json.loads((ROOT/'release/release.json').read_text(encoding='utf-8'))['video'];story=[]
 def add(*items):story.extend(items)
 def page(n,title):add(PageBreak(),P(f'{n:02d} / 亲安 · 技术说明','small'),P(title,'h1'))
 add(Spacer(1,55),P('亲安','title'),P('面向老人的多模态<br/>反诈辅助核验 Web 应用','title'),P('第九届 AI WEB 网页开发挑战赛<br/>技术文档 · 本机研究辅助版 3.0','h2'),Spacer(1,32),P('从收到可疑材料，到找到核实线索，再通过预留号码独立联系家人。AI只提供辅助证据，不确认身份，不代替付款决定。'),Spacer(1,42),P('队名：'+team['team_name']),P('学校：'+team['school']),P('成员：'+'　'.join(team['members'])),P('指导老师：'+team['advisor']),Spacer(1,30),P('整理日期：2026年11月11日。演示视频按使用者要求暂不录制；本文与源码供先行检查。','small'))
 page(1,'问题、用户与产品闭环')
 add(P('主要用户是收到可疑视频、语音或照片的老人本人。子女不是唯一入口；系统保留事先确认的家人常用号码，避免由可疑消息控制整个核实渠道。'),P('核心场景','h2'),P('01 亲友求助：上传一段预录视频，分别检查人脸画面、声音和转写表达。无论分数高低，都能进入预留联系人。'),P('02 假专家宣传：演示合成声音与冒用权威、高收益等表达的独立线索。专家形象或AI生成本身都不等于诈骗。'),P('03 图片生成与编辑：分别呈现整图生成和局部异常定位，不把异常热图当成已证实的修改区域。'),P('交互约束','h2'),P('单个材料不超过100MB，视频不超过3分钟。页面提供明确进度、失败原因、报告、转写校正、打印与JSON导出。手机浏览器可使用tel链接打开拨号程序，由使用者确认；系统不自动拨号。'),P('联系号码只存于当前浏览器，不进入识别模型或解释模型。原始上传材料处理后清理；报告保留模型结果、转写、描述和文件哈希。'))
 page(2,'系统结构与前端工程')
 add(architecture(),P('前端采用React、TypeScript和Vite，使用独立视图组件管理上传、报告、联系人、情景练习、历史与实测页。非首页组件按需加载，日常运行直接使用已构建静态文件，不要求每次启动Node开发服务器。'),P('核验任务在本机执行。GPU模型通过锁串行调度，声音模型复用已核验的CPU权重缓存，避免每个5秒片段重复初始化。SQLite保存报告，内存只保留最近任务，移除内存任务后仍能从数据库恢复完成报告。'),P('页面刷新可用当前会话的任务编号恢复轮询；不会把原始材料放入浏览器永久存储。对于模型缺失、无可用人脸、静音或损坏材料，返回失败或无法判断，不伪造分数。'),P('后端是AI能力接入与任务编排层；比赛呈现以网页交互、核实闭环、证据解释和前端工程为重点。'))
 page(3,'识别方法、训练与版本选择')
 add(P('视频画面','h2'),P('当前研究版本由X-CLIP短片段人脸时序模型与VideoMAE人脸时序模型交叉核验。前者复现作者的4组8帧、固定人脸框与JPEG92预处理；后者使用16帧人脸区域。两者都是学习图像/时序表示，不是读取一项“AI像素标签”。'),P('本地训练冻结VideoMAE编码器，只更新分类头。300段素材按150个源视频组划分：100组训练、25组验证、25组测试；训练/验证采用inswapper，初步测试采用uniface。之后在原验证来源组上拟合两个模型的非负正则校准层，不把拟合成绩当作独立验证。'),P('声音、图像和解释','h2'),P('声音采用2026年公开的XLS-R/AASIST权重，5秒切片，标签方向按作者定义映射。整图生成沿用独立图像分类器，局部编辑采用TruFor。图像与声音没有伪造成一个统一诈骗概率。'),P('用户原有图片分类头训练结果保留。4000张混合来源图像的留出成绩虽然较高，但商品诊断、压缩和用户回归显示明显分布差异，未据此直接替换网页模型。商品多视角训练与额外候选检测器的失败也保留记录。'),P('启用的视频版本：'+html.escape(release['version']),'small'))
 page(4,'实际测试结果与边界')
 rows=[['项目','样本数','平衡准确率','真实误报率','合成漏检率']]
 for name,m in [('视频最终新来源组',video),('中文同文本语音对照',audio),('商品图原模型诊断',metric('domain-evaluation.json','whole_image')),('商品图JPEG60诊断',metric('domain-evaluation.json','jpeg60'))]:rows.append([name,str(m['n']),pct(m['balanced_accuracy']),pct(m['real_false_positive_rate']),pct(m['fake_miss_rate'])])
 add(table(rows),Spacer(1,18),P('视频最终复核使用100个新源视频ID：真实、inswapper、uniface各100段，排除本地训练、校准和此前诊断来源组，并检查字节哈希重叠。实际处理覆盖率为'+pct(vd['coverage'])+'；拒判另列，不算作正确分类。'),P('音频对照包含60条公开中文电话真人语音和60条同文本通用TTS语音，三种通用声音。它不是最新声音克隆或老人场景基准，人物独立性与预训练来源重合未核实，不能宣传为通用97.5%准确率。'),P('失败实验同样重要','h2'),P('视频最初50段得到90%，扩大到200段后仅70%；这说明小样本结论会偏乐观。商品模型在压缩图、局部编辑和新生成器上也有漏检。最终页面公开这些变化，并保留无法判断及可信回拨流程。'),P('公开数据标签沿用作者定义；源视频ID隔离不等于真实人物身份隔离。未验证的GPT/Sora等生成器不作检出率承诺。'))
 page(5,'有来源的本地解释与安全约束')
 add(P('解释助手采用本地Qwen3-0.6B，素材、转写和问题不发送至云端API。工作流先读取本次报告，再用中文二元词BM25检索审核过的官方反诈资料，最后由模型选择结构化核实建议。'),P('当前知识库是小型、版本化的审核资料集，并非完整法规或反诈数据库。展示实际检索来源链接和工具步骤，方便评审复查。主要来源包括张家港市公安局、司法部智慧普法平台和中央网信办公开提示。'),P('输出采用动作与摘要枚举，不允许模型自由生成收款号码、电话、链接、转账指令或身份结论。引用必须来自实际检索结果，动作须与所引资料一致；缺失模型或输出校验失败时，明确标为检索兜底，不伪称模型已给出回答。'),P('功能定位','h2'),P('这是受限、只读的AI工作流。它不执行外部消息、拨号或支付，也不把固定编排包装成无限自主Agent。安全提醒与联系家人保留在产品流程中，避免因分类低分产生“可以放心付款”的错觉。'),P('真实运行证据见reports/advisor-smoke.json；模型选择通过结构、引用和动作校验。测试还覆盖提示注入内容、伪造来源和越权动作。'))
 page(6,'验证、运行与可恢复训练')
 add(P('本轮自动验收：'+html.escape(str(accept.get('summary','详见验收记录')))),P('启动网站','h2'),P('在项目根目录双击start-background.cmd，等待提示“亲安已启动”，浏览器访问http://127.0.0.1:8010。停止网站使用stop.cmd。开发时运行python run.py；关闭该终端会停止服务。'),P('PyCharm打开与训练','h2'),P('打开outputs/qinan目录，终端切到该目录。图片训练入口是train_images.py；视频分类头入口是train_video_head.py。图片目标总轮数通过--epochs设置，而不是每执行一次自动追加相同轮数。训练使用编码器冻结方式，不是全参数微调。'),P('Ctrl+C在当前批次后安全保存；重新运行同一数据清单和输出目录可恢复优化器、轮次和进度。Windows文件占用时使用独立恢复文件和重试，不覆盖用户已有balanced-v1成果。不同实验目录相互独立，网站启用权重使用固定版本。'),P('测试命令','h2'),P('python -m unittest tests test_domain test_advisor test_checkpoint_io -q<br/>npm run build --prefix web<br/>python verify_delivery.py'),P('浏览器已完成部分页面实测；后续桌面自动操控因无法可靠确认窗口网址被工具停止。没有将这一限制写成“所有浏览器已自动通过”。最终需由使用者检查桌面外观、手机拨号程序、打印和自身素材效果。','small'))
 page(7,'原创改进、交付与来源')
 add(P('项目自身的工作包括老人优先的核实闭环、独立模态证据编排、可信联系人、转写纠正、实际模型与版本展示、断点训练恢复、冻结编码器校准对比、来源组复核及有引用的受限解释。基础模型与通用算法不声称为团队原创。'),P('交付内容','h2'),P('可运行的本机网站、React/TypeScript源码与构建结果、Python后端和训练入口、启用版本清单、实测报告摘要、当前使用说明、文件说明、截图清单、技术PDF及可审阅源码包。演示视频按使用者要求暂不录制；也未替使用者公开仓库或向比赛平台提交。'),P('材料检查与下一步','h2'),P('由团队先检查网站与技术材料，再确认分工、仓库信息及最终参赛提交。现有误报、漏检与泛化边界不能通过宣传文案消除；后续应扩充真实老人接收渠道、不同人物与不同生成方法的独立数据，保留未参与调参的测试组。'),P('主要来源与许可记录','h2'))
 refs=[('正式赛道要求','https://www.boxuegu.com/matchTrack/detail/?id=10037'),('RTFS-10K视频数据（CC-BY-SA-4.0）','https://huggingface.co/datasets/kontur-ai/rtfs-10k'),('FraudBench商品数据（CC-BY-NC-SA-4.0）','https://huggingface.co/datasets/TristanYan/FraudBench'),('X-CLIP人脸候选（研究用途与上游数据限制）','https://huggingface.co/zodumair/sifta-deepfake-detector'),('声音模型（CC-BY-NC-4.0）','https://huggingface.co/eliya/forensics_0.3B_xlsr_wild_deepfake_classifier'),('Qwen3解释模型（Apache-2.0）','https://huggingface.co/Qwen/Qwen3-0.6B'),('TruFor（作者非营利许可）','https://github.com/grip-unina/TruFor')]
 for label,url in refs:add(P(f'<link href="{html.escape(url)}" color="#315e48">{html.escape(label)}</link>','small'))
 add(P('其余模型与库见docs/THIRD_PARTY.md，各自模型卡、固定revision与文件哈希保存在models下。源码包不包含私人照片、联系人、历史数据库或全部数据集，第三方权重按安装入口取得。','small'))
 def footer(c,doc):
  c.setStrokeColor(colors.HexColor('#d8e1d1'));c.line(42,42,553,42);c.setFont('CN',8);c.setFillColor(GRAY);c.drawString(42,28,'亲安守望队 / 大连东软信息学院 / 2026-11-11');c.drawRightString(553,28,f'{doc.page} / 技术文档')
 SimpleDocTemplate(str(OUT/'亲安_技术文档.pdf'),pagesize=(595.28,841.89),rightMargin=44,leftMargin=44,topMargin=42,bottomMargin=58,title='亲安多模态反诈辅助核验技术文档',author=team['team_name']).build(story,onFirstPage=footer,onLaterPages=footer)
 print('Built',OUT/'亲安_技术文档.pdf')
if __name__=='__main__':main()
