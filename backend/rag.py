"""Versioned local hybrid RAG. All passages are reviewed paraphrases, never live web instructions."""
import hashlib,json,re
from functools import lru_cache
from urllib.parse import urlparse
from .knowledge import DOCUMENTS,tokens

EXTRA=[
 dict(id='K6',title='公安提醒：涉案保密与安全账户',url='https://gaj.beijing.gov.cn/xxfb/jwbd/202601/t20260115_4433143.html',date='2026-01-15',snippet='冒充办案人员可能展示假证件，并要求案件保密；不要按对方指示转账到所谓安全账户，应另找官方渠道核实。',action='pause'),
 dict(id='K7',title='远程控制和屏幕共享风险',url='https://legalinfo.moj.gov.cn/zhfxfzzx/fzzxyw/202506/t20250620_521303.html',date='2025-06-20',snippet='诈骗者可能借助共享屏幕读取账户和验证码。不要应陌生客服要求展示银行操作界面或提供验证信息。',action='protect'),
 dict(id='K8',title='安全账户与资金核查要求',url='https://legalinfo.moj.gov.cn/zhfxfzzx/fzzxyw/202506/t20250620_521303.html',date='2025-06-20',snippet='对方声称资金有风险，并要求转入指定账户进行核查，是典型风险要求；先暂停操作再独立核实。',action='pause'),
 dict(id='K9',title='公开案例：假好友视频借款',url='https://www.shanwei.gov.cn/gdsw110/zwgk/wgk/content/post_924988.html',date='2023-05-26',snippet='警方发布的案例中，骗子用假好友视频取得信任，以保证金和账户过账为由诱导汇款。应使用原先保存的号码重新联系本人。',action='callback')
]
CORPUS=DOCUMENTS+EXTRA
EXPANSIONS=[(r'公检法|公安|民警|涉案|洗钱|保密|安全账户','公安 涉案 保密 安全账户'),(r'投屏|共享|远程|控制手机','共享屏幕 远程控制 验证码'),(r'孩子|女儿|儿子|孙子|妈妈|借钱|周转|家人','亲友 熟人 借款 视频 核实'),(r'口令|六位|密码|验证码','验证码 银行卡 个人信息')]

def manifest():
 raw=json.dumps(CORPUS,ensure_ascii=False,sort_keys=True).encode()
 return dict(version='qinan-guidance-20261114-v1',sha256=hashlib.sha256(raw).hexdigest(),passages=len(CORPUS),strategy='BM25 + character TF-IDF cosine + scenario expansion + reciprocal-rank fusion',review='人工审核的官方资料摘要；不是实时联网全文库',sources=[{k:d[k] for k in ('id','title','url','date')} for d in CORPUS])

@lru_cache(maxsize=1)
def index():
 from sklearn.feature_extraction.text import TfidfVectorizer
 vectorizer=TfidfVectorizer(analyzer='char',ngram_range=(2,4),sublinear_tf=True)
 matrix=vectorizer.fit_transform([d['title']+' '+d['snippet'] for d in CORPUS])
 return vectorizer,matrix

def retrieve(query,limit=3):
 from collections import Counter
 import math
 query=str(query)[:1600]
 expanded=query+' '+ ' '.join(v for p,v in EXPANSIONS if re.search(p,query))
 vectorizer,matrix=index();dense=(matrix@vectorizer.transform([expanded]).T).toarray().ravel()
 counts=[Counter(tokens(d['title']+d['snippet'])) for d in CORPUS];avg=sum(sum(c.values()) for c in counts)/len(counts)
 terms=set(tokens(expanded));bm=[]
 for c in counts:
  score=0.
  for term in terms:
   tf=c[term]
   if tf:
    df=sum(v[term]>0 for v in counts);score+=math.log(1+(len(counts)-df+.5)/(df+.5))*tf*2.5/(tf+1.5*(.25+.75*sum(c.values())/avg))
  bm.append(score)
 ranks=[]
 for scores in (bm,dense):ranks.append({i:n+1 for n,i in enumerate(sorted(range(len(CORPUS)),key=lambda i:(-float(scores[i]),i)))})
 rows=[]
 for i,doc in enumerate(CORPUS):
  if bm[i]<=0 and dense[i]<=0:continue
  if urlparse(doc['url']).scheme!='https':raise ValueError('Unsafe corpus URL')
  rows.append(dict(doc,retrieval_score=round(sum(1/(60+r[i]) for r in ranks),6),bm25_score=round(bm[i],5),cosine_score=round(float(dense[i]),5),corpus_version=manifest()['version']))
 return sorted(rows,key=lambda d:(-d['retrieval_score'],d['id']))[:max(1,min(int(limit),5))]

def source(source_id):
 return next((dict(d) for d in CORPUS if d['id']==source_id),None)
