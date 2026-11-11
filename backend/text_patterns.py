"""Local learned text pattern inference. Never used to judge acoustic authenticity."""
import re,json
from functools import lru_cache
import numpy as np
from bootstrap import ROOT
LABELS=['冒充公检法 / 涉案施压','理赔退款 / 诱导操作','扣费会员 / 取消业务','冒充熟人 / 借钱求助','普通服务 / 营销类']
def normalize(text):
 text=re.sub(r'https?://\S+','网址',text)
 text=re.sub(r'\d+','数',text)
 return re.sub(r'[^\u4e00-\u9fffA-Za-z]','',text).lower()
@lru_cache(maxsize=1)
def load():
 path=ROOT/'models/text-patterns';meta=json.loads((path/'config.json').read_text(encoding='utf-8'))
 z=np.load(path/'weights.npz',allow_pickle=False)
 return meta,{t:i for i,t in enumerate(meta['vocabulary'])},z['idf'],z['coef'],z['intercept']
def predict(text):
 meta,vocab,idf,coef,intercept=load();s=normalize(text);counts={}
 for n in range(2,5):
  for i in range(len(s)-n+1):
   key=vocab.get(s[i:i+n])
   if key is not None:counts[key]=counts.get(key,0)+1
 if len(s)<8 or len(counts)<4:return dict(status='insufficient',level='uncertain',title='文字太少，暂不能判断套路',patterns=[],version=meta['version'])
 ids=np.asarray(list(counts),dtype=int);x=(1+np.log(list(counts.values())))*idf[ids];x/=max(np.linalg.norm(x),1e-12)
 logits=(coef[:,ids]@x+intercept)/meta['temperature'];prob=np.exp(logits-logits.max());prob/=prob.sum();order=np.argsort(-prob);top=int(order[0]);strength=float(prob[top]);margin=float(prob[order[0]]-prob[order[1]])
 level='attention' if top!=4 and strength>=meta.get('warning_threshold',1.01) else 'uncertain'
 return dict(status='completed',level=level,title=('内容接近“'+LABELS[top]+'”套路') if level=='attention' else '先核对对方身份和要求',patterns=[dict(label=LABELS[int(i)],score=round(float(prob[i]),4)) for i in order[:3]],version=meta['version'],experimental=True,note='实验分类器只提示相近套路；五分类实测约70%，不能可靠裁决诈骗。分数不是被骗概率。')
