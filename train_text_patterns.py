"""Train a reproducible, resumable character-pattern classifier, not an AI author detector.
Author Hard splits retained; normalized duplicates crossing splits removed entirely.
Run: python train_text_patterns.py --epochs 12 (same command resumes).
"""
import bootstrap
import argparse, hashlib, json, re, os, uuid, time
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import classification_report, confusion_matrix, log_loss
from scipy.special import softmax
from backend.text_patterns import normalize, LABELS

ROOT=bootstrap.ROOT; OUT=ROOT/'models/text-patterns'; DATA=ROOT/'data/text-fraud/scamgen'
def main():
 p=argparse.ArgumentParser();p.add_argument('--epochs',type=int,default=12);args=p.parse_args();OUT.mkdir(exist_ok=True)
 import msvcrt
 lock=(OUT/'training.lock').open('a+b');lock.seek(0);lock.write(b'0');lock.flush();lock.seek(0)
 try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 except OSError:raise RuntimeError('此目录已经有文字训练进程，请勿同时启动两份。')
 raw={}
 for split in ['train','dev','test']:
  items={}
  for line in (DATA/f'Hard_{split}.txt').read_text(encoding='utf-8-sig').splitlines():
   if '\t' not in line:continue
   text,label=line.rsplit('\t',1);text=normalize(text)
   if len(text)>=8:items.setdefault(text,set()).add(int(label))
  raw[split]=items
 crossed=set(raw['train'])&set(raw['dev'])|set(raw['train'])&set(raw['test'])|set(raw['dev'])&set(raw['test'])
 splits={k:[(t,next(iter(labels))) for t,labels in rows.items() if t not in crossed and len(labels)==1] for k,rows in raw.items()}
 fingerprint=hashlib.sha256(json.dumps(splits,ensure_ascii=False).encode()).hexdigest()
 texts,labels=zip(*splits['train']);y=np.asarray(labels);vec=TfidfVectorizer(analyzer='char',ngram_range=(2,4),max_features=60000,min_df=3,sublinear_tf=True,dtype=np.float32);X=vec.fit_transform(texts)
 dev,ydev=zip(*splits['dev']);D=vec.transform(dev);ydev=np.asarray(ydev)
 test,ytest=zip(*splits['test']);T=vec.transform(test);ytest=np.asarray(ytest)
 model=SGDClassifier(loss='log_loss',alpha=1e-5,learning_rate='optimal',random_state=27,average=False)
 state=OUT/'last.npz';start=0;best=float('inf');bestcoef=None;bestintercept=None
 candidates=[]
 for path in [state,*OUT.glob('last-recovery-*.npz')]:
  if not path.exists():continue
  try:
   with np.load(path,allow_pickle=False) as z:candidates.append((int(z['epoch']),path))
  except (OSError,ValueError,KeyError):continue
 if state.exists() and not candidates:raise RuntimeError('已有检查点无法读取，请保留排查，不会从零覆盖。')
 if candidates:
  state_to_load=max(candidates,key=lambda item:item[0])[1]
  with np.load(state_to_load,allow_pickle=False) as z:
   if str(z['fingerprint'])!=fingerprint:raise RuntimeError('Dataset changed; use a new output directory, do not silently resume.')
   start=int(z['epoch']);best=float(z['best']);bestcoef=z['bestcoef'];bestintercept=z['bestintercept']
   model.partial_fit(X[:5],y[:5],classes=np.arange(5));model.coef_=z['coef'];model.intercept_=z['intercept'];model.t_=float(z['t'])
 print('split counts', {k:len(v) for k,v in splits.items()},'cross-split duplicates removed',len(crossed),flush=True)
 counts=np.bincount(y,minlength=5);weights=len(y)/(5*counts)
 for epoch in range(start,args.epochs):
  order=np.random.default_rng(27+epoch).permutation(len(y))
  for offset in range(0,len(y),512):
   ids=order[offset:offset+512];model.partial_fit(X[ids],y[ids],classes=np.arange(5),sample_weight=weights[y[ids]])
  # Epoch-boundary checkpoints: interruption replays at most one deterministic epoch.
  loss=log_loss(ydev,softmax(model.decision_function(D),axis=1),labels=np.arange(5))
  if loss<best:best=loss;bestcoef=model.coef_.copy();bestintercept=model.intercept_.copy()
  temp=OUT/('last-recovery-'+uuid.uuid4().hex+'.npz');np.savez_compressed(temp,coef=model.coef_,intercept=model.intercept_,t=model.t_,epoch=epoch+1,fingerprint=fingerprint,best=best,bestcoef=bestcoef,bestintercept=bestintercept)
  for attempt in range(7):
   try:os.replace(temp,state);break
   except PermissionError:
    if attempt==6:print('主文件被占用，保留恢复文件，下次自动读取：',temp.name,flush=True)
    else:time.sleep(.1*(attempt+1))
  print(f'epoch={epoch+1}/{args.epochs} validation_loss={loss:.5f} best={best:.5f}',flush=True)
 # Temperature selected only on validation set, not test.
 vd=D@bestcoef.T+bestintercept;temperatures=np.linspace(.5,3,101);temperature=float(min(temperatures,key=lambda t:log_loss(ydev,softmax(vd/t,axis=1),labels=np.arange(5))))
 vp=softmax(vd/temperature,axis=1);vpred=vp.argmax(1)
 # An abstaining warning policy, tuned only on validation normal-service records.
 warning_threshold=1.01
 for cut in np.linspace(.6,.999,400):
  warning=(vpred!=4)&(vp.max(1)>=cut)
  if np.mean(warning[ydev==4])<=.05:warning_threshold=float(cut);break
 td=T@bestcoef.T+bestintercept;probs=softmax(td/temperature,axis=1);pred=probs.argmax(1)
 np.savez_compressed(OUT/'weights.npz',coef=bestcoef,intercept=bestintercept,idf=vec.idf_)
 vocab=[None]*len(vec.vocabulary_)
 for token,index in vec.vocabulary_.items():vocab[index]=token
 meta=dict(version='qinan-text-patterns-r1',labels=LABELS,vocabulary=vocab,temperature=temperature,warning_threshold=warning_threshold,ngram_range=[2,4],fingerprint=fingerprint,source='ScamGen Hard (author template-augmented Chinese scripts, 2024)',scope='Five author script categories. Others means ordinary marketing examples here, not all safe conversations. Not a fraud probability.')
 (OUT/'config.json').write_text(json.dumps(meta,ensure_ascii=False),encoding='utf-8')
 report=dict(split_counts={k:len(v) for k,v in splits.items()},removed_cross_split_normalized_duplicates=len(crossed),fingerprint=fingerprint,epochs=args.epochs,selection='minimum validation log loss; temperature validation only',temperature=temperature,classification=classification_report(ytest,pred,target_names=LABELS,output_dict=True),confusion_matrix=confusion_matrix(ytest,pred).tolist(),normal_false_alert_rate=float(np.mean(pred[ytest==4]!=4)),scam_missed_as_other_rate=float(np.mean(pred[ytest!=4]==4)),log_loss=float(log_loss(ytest,probs)),limitations=['Author Hard splits retained; author reports held-out scenarios. Independent provenance of all templates not verified.','Normalized exact cross-split duplicates removed; semantic/template overlap remains possible.','Augmented telephone scripts, not representative of all real chat screenshots. Scores are pattern similarity, not population fraud probability.','Other class is narrow marketing/ordinary service examples. No general safe-chat guarantee.'])
 warning=(pred!=4)&(probs.max(1)>=warning_threshold)
 report['warning_policy']=dict(threshold=warning_threshold,selection='validation normal-service false warning <=5%; all other outcomes abstain, never call safe',test_normal_false_warning_rate=float(warning[ytest==4].mean()),test_scam_warning_recall=float(warning[ytest!=4].mean()),test_warning_coverage=float(warning.mean()))
 (ROOT/'reports/text-pattern-training.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ['classification','normal_false_alert_rate','scam_missed_as_other_rate','warning_policy']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
