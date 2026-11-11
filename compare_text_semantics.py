"""Compare a frozen Chinese BERT + trained classifier with character baseline.
No encoder fine-tuning. Same author Hard splits, validation-only model selection.
Resumes cached feature batches; does not activate a candidate automatically.
"""
import bootstrap,hashlib,json,time
import numpy as np
import torch
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report,confusion_matrix
from backend.text_patterns import normalize,LABELS
from transformers import AutoTokenizer,AutoModel
ROOT=bootstrap.ROOT
def main():
 torch.set_num_threads(2);folder=ROOT/'models/text-encoder'
 while not (folder/'source.json').exists():print('Waiting for verified official BERT download',flush=True);time.sleep(10)
 source=json.loads((folder/'source.json').read_text())
 assert hashlib.sha256((folder/'model.safetensors').read_bytes()).hexdigest()==source['sha256']['model.safetensors']
 tok=AutoTokenizer.from_pretrained(folder,local_files_only=True)
 model,info=AutoModel.from_pretrained(folder,local_files_only=True,use_safetensors=True,add_pooling_layer=False,output_loading_info=True)
 assert not info['missing_keys'],info['missing_keys']
 model=model.to('cuda',dtype=torch.float16).eval();rows={}
 for split in ['train','dev','test']:
  values={}
  for line in (ROOT/f'data/text-fraud/scamgen/Hard_{split}.txt').read_text(encoding='utf-8-sig').splitlines():
   if '\t' in line:
    t,l=line.rsplit('\t',1);t=normalize(t)
    if len(t)>=8:values.setdefault(t,set()).add(int(l))
  rows[split]=values
 crossed=set(rows['train'])&set(rows['dev'])|set(rows['train'])&set(rows['test'])|set(rows['dev'])&set(rows['test'])
 data={}
 for split,values in rows.items():
  selected=[(t,next(iter(ls))) for t,ls in values.items() if t not in crossed and len(ls)==1]
  # Training limit is fixed before encoding/test; independent of scores.
  if split=='train':selected=sorted(selected,key=lambda r:hashlib.sha256(r[0].encode()).hexdigest())[:12000]
  xs=[];ys=[]
  for start in range(0,len(selected),48):
   batch=selected[start:start+48];identity=hashlib.sha256(json.dumps(batch,ensure_ascii=False).encode()+b'bert-mean256-v1').hexdigest();cache=ROOT/f'runtime/text-features/{identity}.npy';cache.parent.mkdir(exist_ok=True)
   if not cache.exists():
    inputs=tok([x[0] for x in batch],padding=True,truncation=True,max_length=256,return_tensors='pt').to('cuda')
    with torch.inference_mode():
     hidden=model(**inputs).last_hidden_state.float();mask=inputs.attention_mask.unsqueeze(-1);x=((hidden*mask).sum(1)/mask.sum(1)).cpu().numpy()
    temp=cache.with_suffix('.new.npy');np.save(temp,x);temp.replace(cache)
   xs.append(np.load(cache,allow_pickle=False));ys.extend(x[1] for x in batch)
   if start%480==0:print(split,start,'/',len(selected),flush=True)
  data[split]=(np.concatenate(xs),np.asarray(ys))
 del model;torch.cuda.empty_cache();x,y=data['train'];v,vy=data['dev'];t,ty=data['test'];best=None
 for c in [.01,.1,1,10]:
  candidate=LogisticRegression(C=c,max_iter=600,class_weight='balanced').fit(x,y);score=candidate.score(v,vy);print('C',c,'validation accuracy',score,flush=True)
  if best is None or score>best[0]:best=(score,c,candidate)
 score,c,model=best;pred=model.predict(t);out=ROOT/'models/text-semantic-candidate';out.mkdir(exist_ok=True);np.savez_compressed(out/'weights.npz',coef=model.coef_,intercept=model.intercept_)
 report=dict(model='Frozen official Chinese BERT mean pooling + locally trained multinomial logistic head',encoder_revision=source['revision'],train_samples=len(y),validation_samples=len(vy),test_samples=len(ty),selected_C=c,validation_accuracy=score,classification=classification_report(ty,pred,target_names=LABELS,output_dict=True),confusion_matrix=confusion_matrix(ty,pred).tolist(),active=False,limitations=['Author synthetic/template Hard split; not a real elderly screenshot test.','No claim of fraud probability or universal accuracy.','Train subset fixed by SHA ordering, not selected from test performance.'])
 (ROOT/'reports/text-semantic-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False),flush=True)
if __name__=='__main__':main()
