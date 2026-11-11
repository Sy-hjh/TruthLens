"""Read-only experimental evidence; never promotes checkpoints."""
import json
from bootstrap import ROOT

def summary():
 specs=[('图像分类头：原有留出集','balanced-test.json',None,'634张，来源与真实业务存在差异，不能代表通用准确率。'),('商品改图：原模型原图','domain-evaluation.json','whole_image','240张商品图；这是已观察的诊断集。'),('商品改图：原模型压缩图','domain-evaluation.json','jpeg60','同一批图片JPEG60重编码，不是新增样本。'),('商品改图：多视角线性头','domain-candidate.json','clean','独立类别训练，当前误报偏高，未启用。'),('商品改图：多视角MLP压缩图','domain-mlp-candidate.json','jpeg60','压缩鲁棒性有所改善，当前误报偏高，未启用。'),('视频：原始预训练模型','video-diagnostic.json','metrics','18段初步诊断，不能代表老人收到视频的总体准确率。'),('视频：人脸场景分类头','video-face-adapt-test.json','metrics','计划50段留出测试，源视频隔离、换脸生成器留出；非身份隔离，拒判另计。'),('局部修图：新模型诊断','integrity-v9-diagnostic.json','metrics','60张商品诊断图，汽车领域迁移测试，未自动启用。')]
 specs += [('视频分类头：扩大200段复核','video-release-check.json','metrics','新的100个来源组；结果由50段90%下降到70%，不能用小样本宣传泛化。'),('双视频模型：已观察诊断集','video-fusion-calibration.json','observed_diagnostic','两个冻结视频模型，校准层只拟合旧验证组；这里不是最终新测试。'),('声音：中文同文本对照','audio-mandarin-check.json','metrics','60组真人电话语音/三种通用TTS，不是最新克隆声或老人业务准确率。'),('视频：最终来源组复核','video-final-evaluation.json','metrics','100个新来源组，真实及两种换脸各100段；未参与本地训练或校准。')]
 specs += [('GenD视频：已观察300段对照','gend-check.json','observed300','用于方案比较，不能冒充新测试。'),('GenD视频：新来源180段复核','gend-final.json','fresh180','60个新增来源ID，固定0.5阈值；不代表所有生成器，预训练重叠未知。'),('B-Free图片：原图','bfree-check.json','original','240张局部改图诊断，未启用。'),('B-Free图片：JPEG60','bfree-check.json','jpeg60','同一批压缩测试，未启用。'),('Detectra图片诊断','detectra-check.json','original','使用作者384输入与0.65阈值，局部编辑漏检严重，未启用。')]
 specs += [('Smaug整图生成：校准后留出测试','smaug-whole-final.json','whole_image_test','634张，阈值只用另632张验证集拟合；字节无交集，上游训练重叠未知；不是局部P图或通用GPT准确率。'),('Smaug局部改图诊断','smaug-check.json','original','240张局部改图大量漏检，不提供可靠局部修改判断。')]
 specs += [('声音克隆：主模型留出原音','verispoof-test-channels.json','clean','624段、6名留出说话人，其中真人仅32段；固定作者阈值；不代表所有克隆声音。'),('声音克隆：主模型AAC压缩','verispoof-test-channels.json','aac32','同一624段压缩后复测，不是新增独立样本。'),('声音克隆：主模型电话带宽','verispoof-test-channels.json','phone8','同一624段8kHz带宽模拟；不是实际全平台通话测试。'),('声音双重检查：已观察原音复核','voice-cascade-check.json','test_clean','主模型阴性时第二声学模型复查；已观察集的方案复核，不能冒充新的独立测试。'),('声音双重检查：已观察AAC复核','voice-cascade-check.json','test_aac32','同一批624段压缩复核，真人误报1/32；不是通用准确率。'),('声音双重检查：已观察电话复核','voice-cascade-check.json','test_phone8','同一批624段；漏检4/592，上游预训练重叠未知。'),('声音双重检查：通用TTS对照复核','voice-cascade-check.json','phone_clean','120段（60真人/60通用TTS），误报2、漏检3；已观察的补充诊断。')]
 rows=[]
 keys=('n','real_count','fake_count','false_positives','false_negatives','real_false_positive_rate','fake_miss_rate','balanced_accuracy','accuracy')
 for title,file,key,note in specs:
  path=ROOT/'reports'/file
  try:
   if path.exists():report=json.loads(path.read_text(encoding='utf-8'))
   else:
    archive=ROOT/'docs/benchmarks.json'
    report=json.loads(archive.read_text(encoding='utf-8'))['reports'][file] if archive.exists() else None
    if report is None:continue
   metric=report[key] if key else report
   metric=metric.get('metrics',metric)
   rows.append(dict(title=title,metrics={k:metric.get(k) for k in keys},note=note,report=file,rejected=len(report.get('rejected',[]))))
  except (ValueError,KeyError,TypeError):continue
 releases={}
 for kind in ('video','audio','image','domain'):
  path=ROOT/'models'/('active-'+kind+'.json')
  releases[kind]=json.loads(path.read_text(encoding='utf-8')).get('version') if path.exists() else '原有模型' if kind in ('video','audio') else '未启用'
 return dict(experiments=rows,releases=releases,warning='实验结果按数据集分别展示。重复查看过的诊断集不能当作全新独立测试，分数不是真实性或诈骗概率。')
