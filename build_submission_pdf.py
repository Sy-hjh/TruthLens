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
 nodes=[(5,195,490,48,'React + TypeScript网页：上传、报告、家人联系、练习'),(5,117,490,48,'FastAPI任务编排：文件校验、独立检测、清理、记录'),(5,35,153,50,'视频 / 声音 / 图像模型'),(174,35,152,50,'截图OCR / 内容分析'),(342,35,153,50,'预警来源与情景练习')]
 for x,y,w,h,label in nodes:d.add(Rect(x,y,w,h,rx=7,ry=7,fillColor=LIGHT,strokeColor=colors.HexColor('#b8c9ab')));d.add(String(x+w/2,y+h/2-4,label,fontName='CN',fontSize=10,textAnchor='middle',fillColor=GREEN))
 for x1,y1,x2,y2 in [(250,195,250,165),(250,117,82,85),(250,117,250,85),(250,117,418,85)]:d.add(Line(x1,y1,x2,y2,strokeColor=GRAY));d.add(Polygon([x2-3,y2+6,x2,y2,x2+3,y2+6],fillColor=GRAY,strokeColor=GRAY))
 return d

def main():
 team=json.loads((ROOT/'team.json').read_text(encoding='utf-8'));story=[]
 def add(*items):story.extend(items)
 def page(n,title):add(PageBreak(),P(f'{n:02d} / 亲安 · 2026-11-11修订','small'),P(title,'h1'))
 add(Spacer(1,45),P('亲安','title'),P('面向老人的多模态<br/>反诈辅助核验 Web 应用','title'),P('第九届 AI WEB 网页开发挑战赛<br/>技术文档 · 评审检查版','h2'),Spacer(1,35),P('收到可疑材料 → 分项检查 → 看懂线索 → 联系事先保存的家人号码。检测不确认人物身份，也不代替付款决定。'),Spacer(1,40),P('队名：'+team['team_name']),P('学校：'+team['school']),P('成员：'+'　'.join(team['members'])),P('指导老师：'+team['advisor']),Spacer(1,25),P('本版已更新模型与交互，未录制演示视频，未向比赛平台提交。','small'))
 page(1,'主要用户与使用闭环')
 add(P('主要用户是老人本人。先上传已经收到的视频、语音或照片，不要求实时监控通话。家人号码应在平时确认并预留，避免用可疑消息提供的新号码自证身份。'),P('三个演示场景','h2'),P('亲友求助视频：分别检查人脸操纵、声音合成；聊天截图另做OCR与要求分析。假专家宣传：演示合成声音和催促付款等独立线索。照片：检查整图生成信号，暂不提供可靠局部P图结论。'),P('适老交互','h2'),P('报告先给出当前应注意的线索，再给出两步核实行动。发现合成线索用红色，没有明确结论用黄色，检测失败明确说明。取消重复问答、误导性热力图、原始分数条和老人界面的模型仓库名称。详细检测数据仍可导出。'),P('信任边界','h2'),P('AI生成不等于诈骗；没有检出也不等于真实。可信联系人保存在当前浏览器。手机上的电话链接可唤起拨号程序，由本人确认。当前本机单用户版不增加登录门槛；未来公开多用户部署必须先增加认证与记录隔离。'))
 page(2,'网页与后端结构')
 add(architecture(),P('React、TypeScript、Vite构建网页。上传、报告、联系人、练习、记录和研究实测页分别维护，非首页按需载入。FastAPI负责上传校验、任务编排与本机推理，SQLite保存核验记录。'),P('文件最大100MB，视频最长3分钟。任务可显示进度并在刷新后继续查询。原始上传材料在处理完成或失败后清理；报告保存分项结果、截图提取文字与哈希，不保留原始上传。'),P('图片新模型在独立进程和独立依赖目录中执行，不覆盖音频、视频所用的Transformers版本。模型文件来自固定版本，权重哈希核验；不执行远程模型代码，不把私人材料发送给外部识别API。'))
 page(3,'识别方法与版本选择')
 add(P('视频：GenD CLIP','h2'),P('使用公开训练权重，严格载入本地架构。均匀采样8帧，以YuNet定位人脸，裁剪边界放大1.3倍，经过CLIP预处理，计算归一化视觉特征的二分类输出，最后取帧均值。固定0.5阈值。无可用人脸时拒判；不确认人物身份。旧VideoMAE分类头与X-CLIP融合版本保留用于比较，不再作为当前默认。'),P('图片：Smaug整图生成检测','h2'),P('使用公开视觉编码器与分类层，按作者方案处理三个528像素视图并平均logit。阈值只由632张验证图片选择：在真实误报率不超过5%的条件下最大化平衡准确率，确定为0.007；之后才运行634张测试图片。原始输出不是诈骗概率，不在老人报告中放大展示。'),P('声音与文字','h2'),P('声音直接输入波形给VeriSpoof-Plus，8秒窗口、4秒步长，以作者固定似然比0为阈值。主模型未检出时，由XLS-R/AASIST复查录音中间5秒，阈值0.70。不同分数不平均，不做语音转写或话术匹配。聊天截图另用本机RapidOCR与Qwen分析原文要求，引用必须能在原文逐字找到。'),P('未通过的能力','h2'),P('TruFor定位、B-Free、Detectra和Smaug的局部改图诊断均未达到可靠效果。已撤下热力图与可靠P图识别宣称。用户原AI改图仍有漏检，不能用新整图测试成绩遮掩。'))
 page(4,'按任务报告真实结果')
 v=metric('gend-final.json','fresh180')['metrics'];im=metric('smaug-whole-final.json','whole_image_test')['metrics'];a=metric('verispoof-test-channels.json','clean')['metrics']
 rows=[['任务 / 数据','有效样本','平衡准确率','真实误报','合成漏检']]
 for name,m in [('新来源人脸换脸',v),('整图生成留出集',im),('克隆声主模型原音',a)]:rows.append([name,m['n'],pct(m['balanced_accuracy']),str(m['false_positives'])+'/'+str(m['real_count']),str(m['false_negatives'])+'/'+str(m['fake_count'])])
 add(table(rows),Spacer(1,18),P('视频计划180段、60个新来源ID：179段可用，1段无可用人脸，覆盖率99.4%。有效样本普通准确率93.3%；若将拒判也算未成功，计划样本正确率92.8%。来源ID排除本地训练、验证和已观察诊断集，但不等于人物身份隔离，上游预训练重合未知。'),P('图片：632张验证、634张测试，无字节哈希交集；真实来源为COCO，合成来源为公开AIGenImages2026的便利抽样。模型未在本地训练这些图片，但上游重合未知；同来源留出成绩不能代表所有GPT图片、局部改图或老人收到的实际材料。'),P('声音：RVCBench共3910段，按说话人隔离2544训练、742验证、624测试。主模型原音误报0/32、漏检1/592；同批AAC误报1、漏检1；电话带宽误报0、漏检8。仅32段真人，传播变体不是新增样本，上游训练重叠未知。双重检查是已观察数据上的补充复核：原音漏检0，AAC误报1、漏检0，电话漏检4；另120段通用TTS对照误报2、漏检3，不冒充新的独立测试。'),P('失败结果同样保留','h2'),P('旧视频方案在300段上平衡准确率83.8%。新视频方案在这批已观察样本上94.3%，随后才验证新来源。图片候选在局部修改240张上仍大量漏检。不能把不同任务相加，宣称整个系统统一达到90%以上。'))
 page(5,'练习与近期诈骗预警')
 add(P('24道教学情景','h2'),P('覆盖亲友求助视频、假专家、养老补贴、共享屏幕、刷单、会员扣费、冒充公检法、假慈善、黄金快递等。选择错误显示红色和“您选错了”，正确选项显示绿色；每轮结束回看错题解释。教学情景明确标记为编写案例，不冒充真实案件。'),P('带来源的预警','h2'),P('从固定允许的12321公开预警栏目提取标题、发布日期和原文链接，配合项目维护的主题防范提示。2026年11月11日实际取得的最近一条为11月9日车辆召回诈骗提醒，不捏造当天新案件。'),P('服务运行时每6小时检查更新，页面也可手动检查。缓存显示最近成功检查时间；网络失败保留旧内容并明确提示。未来日期不发布，不把标题匹配提示写成已读取并验证的完整案情。'),P('删去冗余功能','h2'),P('重复回答的自由问答组件已从老人页面撤下。Qwen现仅在独立聊天截图入口解读提取文字，保留对应原话；不参与声音合成判断，也不判定身份。行动区改为两步简明核实提醒及可信联系人入口。'))
 page(6,'运行、训练与验收')
 add(P('本机启动','h2'),P('双击start-background.cmd，访问http://127.0.0.1:8010；停止用stop.cmd。本机已下载权重，不用重新训练。当前声音主模型使用CUDA与约6.4GB显存，启动器已指定本机GPU版Python。'),P('手动声音续训','h2'),P('先运行python extract_voice_features.py --watch提取固定编码器特征，再执行python train_voice_head.py --wait --epochs 80 --patience 10。冻结编码器，只训练分类头。Ctrl+C保存，运行同一命令恢复优化器、批次与更新进度；80为目标总轮数。'),P('实际训练与选择','h2'),P('本地头训练31轮、最佳第21轮，验证集最差传播通道平衡准确率96.2%；电话带宽部分生成器仍漏检，未启用。预训练VeriSpoof通过验证后才运行624段留出测试，随后另做双模型复核。中断2步再续2步与连续4步权重完全相等。'),P('工程验收','h2'),P('29项后端与训练恢复检查、7项前端阈值检查、生产构建。完整真实权重上传、原始文件清理、静音与坏图拒判另有验收报告。浏览器已实操截图提取与原文分析。打印、手机真实拨号和公开部署仍需最终环境实测；未录制演示视频。'))
 page(7,'交付、来源与后续边界')
 add(P('交付包括网站源码与构建、Python后端、模型安装及训练入口、固定版本清单、聚合实测报告、当前使用说明、文件说明与截图清单。源码包不含私人照片、联系人、数据库、原始训练素材或大权重。'),P('本机保留下载的测试素材与完整报告，方便复核。对外提交时应核对所用数据与权重的非营利、署名及其他限制。本项目不宣称原创基础模型，也未公开发布团队材料。'),P('关键来源','h2'))
 for label,url in [('比赛赛道','https://www.boxuegu.com/matchTrack/detail/?id=10037'),('GenD模型与论文代码','https://github.com/yermandy/GenD'),('Smaug整图模型','https://huggingface.co/abacusai/Smaug-AI-Image-Detector'),('RTFS-10K视频数据','https://huggingface.co/datasets/kontur-ai/rtfs-10k'),('FraudBench局部改图诊断','https://huggingface.co/datasets/TristanYan/FraudBench'),('声学主模型 VeriSpoof-Plus','https://huggingface.co/AustinXiao/VeriSpoof-Plus'),('中文克隆声 RVCBench','https://huggingface.co/datasets/Nanboy/RVCBench-Cloned-Speech'),('12321近期预警','https://12321.cn/warn')]:add(P(f'<link href="{url}" color="#315e48">{label}</link>','small'))
 add(P('全部许可、固定revision和文件校验见docs/THIRD_PARTY.md与release/release.json。后续重点是新增独立中文克隆声、实际传播压缩与老人接收场景；局部P图在独立验证达标前不恢复。','small'))
 def footer(c,doc):
  c.setStrokeColor(colors.HexColor('#d8e1d1'));c.line(42,42,553,42);c.setFont('CN',8);c.setFillColor(GRAY);c.drawString(42,28,'亲安守望队 / 大连东软信息学院 / 2026-11-11');c.drawRightString(553,28,f'{doc.page} / 技术文档')
 SimpleDocTemplate(str(OUT/'亲安_技术文档.pdf'),pagesize=(595.28,841.89),rightMargin=44,leftMargin=44,topMargin=42,bottomMargin=58,title='亲安多模态反诈辅助核验技术文档',author=team['team_name']).build(story,onFirstPage=footer,onLaterPages=footer)
 print('Built',OUT/'亲安_技术文档.pdf')
if __name__=='__main__':main()
