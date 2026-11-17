"""Versioned local hybrid RAG. All passages are reviewed paraphrases, never live web instructions."""
import hashlib,json,re
from functools import lru_cache
from urllib.parse import urlparse
from .knowledge import DOCUMENTS,tokens
from .admin_store import catalog_entries

EXTRA=[
 dict(id='K6',title='公安提醒：涉案保密与安全账户',url='https://gaj.beijing.gov.cn/xxfb/jwbd/202601/t20260115_4433143.html',date='2026-01-15',snippet='冒充办案人员可能展示假证件，并要求案件保密；不要按对方指示转账到所谓安全账户，应另找官方渠道核实。',action='pause'),
 dict(id='K7',title='远程控制和屏幕共享风险',url='https://legalinfo.moj.gov.cn/zhfxfzzx/fzzxyw/202506/t20250620_521303.html',date='2025-06-20',snippet='诈骗者可能借助共享屏幕读取账户和验证码。不要应陌生客服要求展示银行操作界面或提供验证信息。',action='protect'),
 dict(id='K8',title='安全账户与资金核查要求',url='https://legalinfo.moj.gov.cn/zhfxfzzx/fzzxyw/202506/t20250620_521303.html',date='2025-06-20',snippet='对方声称资金有风险，并要求转入指定账户进行核查，是典型风险要求；先暂停操作再独立核实。',action='pause'),
 dict(id='K9',title='公开案例：假好友视频借款',url='https://www.shanwei.gov.cn/gdsw110/zwgk/wgk/content/post_924988.html',date='2023-05-26',snippet='警方发布的案例中，骗子用假好友视频取得信任，以保证金和账户过账为由诱导汇款。应使用原先保存的号码重新联系本人。',action='callback'),
 dict(id='K10',title='警方提示：警惕机票退改签冒充客服',url='https://legalinfo.moj.gov.cn/zhfxfzzx/fzzxyw/202610/t20261007_540408.html',date='2026-10-07',snippet='接到客服说飞机不飞、航班取消或延误，需要退款或理赔时，不要向来电人提供银行卡号、密码或验证码。自行打开航空公司官方渠道核对航班；避免点击对方发来的链接、共享屏幕或给不明账户转账。',action='protect'),
 dict(id='K11',title='中国国航：航班取消时的非自愿退票',url='https://webresource.airchina.com.cn/zh-CN/content/c/2026-04-20/29105.shtml',date='2026-04-20',snippet='以国航公布的规则为例，实际航班取消导致旅客退票，可通过航司或原购票渠道办理非自愿退票。退款通常原路退回，具体以订单和官方渠道为准。',action='source',workflow=True),
 dict(id='K12',title='中国民航局：航班取消或延误时如何通知旅客',url='https://www.caac.gov.cn/INDEX/HLFW/HKLXCS/202303/t20230316_217596.html',date='2023-03-16',snippet='航班取消或延误时，航司会通过官方 App、官网、短信或电话等渠道发布航班变动信息。原购票渠道也会转达航司通知，机场则会通过候机楼广播或航显告知。旅客可自行打开航司官方 App 或原购票订单核对航班状态。',action='source',workflow=True),
 dict(id='K13',title='康奈尔大学教学中心：核实作业中的 AI 使用',url='https://teaching.cornell.edu/generative-artificial-intelligence/ai-academic-integrity',date='',snippet='先查看课程对 AI 使用和披露的要求。对有疑问的作业，可核对参考文献、提纲、草稿或先前提交记录，和学生沟通其论证或创作过程。异常或单一检测信号只适合作为进一步核实的线索，处理应依据校方规则和可验证证据。',action='source',workflow=True),
]
CORPUS=DOCUMENTS+EXTRA
FLIGHT_REFUND_IDS={'K10','K11'}
FLIGHT_NOTICE_ID='K12'
FLIGHT_GUIDANCE_IDS=FLIGHT_REFUND_IDS|{FLIGHT_NOTICE_ID}
FLIGHT_TERMS=re.compile(r'航班|航司|航空公司|机票|飞机')
FLIGHT_NOTICE_TERMS=re.compile(r'通知|通告|告知|短信|广播|航显|联系乘客|联系旅客')
FLIGHT_REFUND_TERMS=re.compile(r'退款|退票|改签|补偿|赔付|赔偿|理赔|卡号|银行卡')
EDUCATION_TERMS=re.compile(r'学生|教师|老师|课程|论文|作文|作业|学术|参考文献')
EDUCATION_CHECK_TERMS=re.compile(r'\bAI\b|人工智能|生成|代写|核实|核查|鉴别|检测|真假|可疑|引用|来源|核对|参考文献|不像.{0,8}写|学术诚信',re.I|re.ASCII)
EXPANSIONS=[(r'公检法|公安|民警|涉案|洗钱|保密|安全账户','公安 涉案 保密 安全账户'),(r'投屏|共享|远程|控制手机','共享屏幕 远程控制 验证码'),(r'孩子|女儿|儿子|孙子|妈妈|借钱|周转|家人','亲友 熟人 借款 视频 核实'),(r'口令|六位|密码|验证码','验证码 银行卡 个人信息')]

def published_corpus():
 return [{k:v for k,v in d.items() if k not in {'status','updated_at'}} for d in catalog_entries('knowledge',CORPUS,published_only=True)]

def manifest(documents=None):
 docs=published_corpus() if documents is None else documents
 raw=json.dumps(docs,ensure_ascii=False,sort_keys=True).encode()
 digest=hashlib.sha256(raw).hexdigest()
 version='qinan-guidance-20261115-v4' if docs==CORPUS else 'qinan-guidance-'+digest[:10]
 return dict(version=version,sha256=digest,passages=len(docs),strategy='BM25 + character TF-IDF cosine + scenario expansion + reciprocal-rank fusion',review='真鉴发布的公开资料摘要',sources=[{k:d[k] for k in ('id','title','url','date')} for d in docs])

@lru_cache(maxsize=4)
def index(passages):
 from sklearn.feature_extraction.text import TfidfVectorizer
 vectorizer=TfidfVectorizer(analyzer='char',ngram_range=(2,4),sublinear_tf=True)
 matrix=vectorizer.fit_transform(passages)
 return vectorizer,matrix

def retrieve(query,limit=3):
 from collections import Counter
 import math
 docs=published_corpus()
 if not docs:return []
 version=manifest(docs)['version']
 passages=tuple(d['title']+' '+d['snippet'] for d in docs)
 query=str(query)[:1600]
 flight=bool(FLIGHT_TERMS.search(query))
 flight_notice=flight and bool(FLIGHT_NOTICE_TERMS.search(query))
 flight_refund=flight and bool(FLIGHT_REFUND_TERMS.search(query))
 education=bool(EDUCATION_TERMS.search(query) and EDUCATION_CHECK_TERMS.search(query))
 expanded=query+' '+ ' '.join(v for p,v in EXPANSIONS if re.search(p,query))
 if flight_notice:expanded+=' 航班取消 通知旅客 官方航班动态'
 if flight_refund:expanded+=' 航班取消 机票退改签 原购票渠道'
 if education:expanded+=' 作业论文 AI使用 课程 学生 草稿 核对引用'
 vectorizer,matrix=index(passages);dense=(matrix@vectorizer.transform([expanded]).T).toarray().ravel()
 counts=[Counter(tokens(text)) for text in passages];avg=max(1,sum(sum(c.values()) for c in counts)/len(counts))
 terms=set(tokens(expanded));bm=[]
 for c in counts:
  score=0.
  for term in terms:
   tf=c[term]
   if tf:
    df=sum(v[term]>0 for v in counts);score+=math.log(1+(len(counts)-df+.5)/(df+.5))*tf*2.5/(tf+1.5*(.25+.75*sum(c.values())/avg))
  bm.append(score)
 ranks=[]
 for scores in (bm,dense):ranks.append({i:n+1 for n,i in enumerate(sorted(range(len(docs)),key=lambda i:(-float(scores[i]),i)))})
 rows=[]
 for i,doc in enumerate(docs):
  if doc['id'] in FLIGHT_REFUND_IDS and not flight_refund:continue
  if doc['id']==FLIGHT_NOTICE_ID and not flight_notice:continue
  if doc['id']=='K13' and not education:continue
  if bm[i]<=0 and dense[i]<=0:continue
  if urlparse(doc['url']).scheme!='https':raise ValueError('Unsafe corpus URL')
  rows.append(dict(doc,retrieval_score=round(sum(1/(60+r[i]) for r in ranks),6),bm25_score=round(bm[i],5),cosine_score=round(float(dense[i]),5),corpus_version=version))
 return sorted(rows,key=lambda d:(-d['retrieval_score'],d['id']))[:max(1,min(int(limit),5))]

def source(source_id):
 return next((dict(d) for d in published_corpus() if d['id']==source_id),None)
