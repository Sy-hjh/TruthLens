"""Resumable frozen-GenD + ordered GRU research head. Never auto-promotes a model.
Old public test groups are explicitly retired into train/validation. A new source
cohort is held out until the best checkpoint and decision threshold are frozen.
"""
import bootstrap,argparse,json,hashlib,re,signal,gc,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.nn import functional as F
from PIL import Image
from checkpoint_io import acquire_training_lock,save_checkpoint,load_latest
from bootstrap import ROOT

class OrderedHead(nn.Module):
 def __init__(self):
  super().__init__();self.project=nn.Sequential(nn.Linear(2048,128),nn.GELU(),nn.Dropout(.1));self.sequence=nn.GRU(128,64,batch_first=True,bidirectional=True);self.output=nn.Linear(128,1)
  nn.init.zeros_(self.output.weight);nn.init.zeros_(self.output.bias)
 def forward(self,x,base,mask,order='original'):
  if order=='reverse':x=x.flip(2)
  elif order=='shuffle':x=x[:,:,[2,0,3,1]]
  elif order=='repeat':x=x[:,:,[0,0,0,0]]
  n,k,t,d=x.shape;difference=torch.cat([torch.zeros_like(x[:,:,:1]),x[:,:,1:]-x[:,:,:-1]],2);z=self.project(torch.cat([x,difference],-1)).reshape(n*k,t,-1);z,_=self.sequence(z);correction=self.output(z.mean(1)).reshape(n,k)
  return ((base+correction)*mask).sum(1)/mask.sum(1)

def group(row):return Path(row['group']).stem.rsplit('_',2)[0]
def gallery(row):
 match=re.search(r'_(\d+-\d+)_(?:man|woman)\.mp4$',row['path']);return match.group(1) if match else None
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def prepare():
 out=ROOT/'models/video-ordered-head';out.mkdir(exist_ok=True);path=out/'data-protocol.json'
 if path.exists():return json.loads(path.read_text(encoding='utf-8'))
 train=json.loads((ROOT/'data/video-final/manifest.json').read_text());val=json.loads((ROOT/'data/video-gend-final/manifest.json').read_text());test=json.loads((ROOT/'data/video-temporal-head-test/manifest.json').read_text())
 assert not ({group(r) for r in train}&{group(r) for r in val})
 assert not ({group(r) for r in train+val}&{group(r) for r in test})
 held_gallery={gallery(r) for r in test if gallery(r)}
 val_gallery={gallery(r) for r in val if gallery(r)}-held_gallery
 # Exclude held-out target-gallery indices. Identity isolation is NOT established.
 train=[r for r in train if gallery(r) is None or gallery(r) not in held_gallery|val_gallery]
 val=[r for r in val if gallery(r) is None or gallery(r) not in held_gallery]
 rows=[dict(r,split=s) for s,items in [('train',train),('val',val),('test',test)] for r in items]
 assert not ({r['sha256'] for r in train+val}&{r['sha256'] for r in test})
 config=dict(rows=rows,seed=20261112,epochs=60,patience=10,lr=.0003,batch_size=16,selection='lowest validation BCE; threshold max validation balanced accuracy at real FPR<=5%; no test tuning',retired='Old video-final and video-gend-final tests are now training/validation; old test scores are historical, not new evidence for this head.',feature_protocol='GenD frozen normalized1024D features; up to4 spans, four ordered frames [0,10,21,31] per32-native-frame span; common face crop1.4; official CLIP processor; GRU temporal residual.',encoder_sha=json.loads((ROOT/'models/gend-clip/source.json').read_text())['sha256'],sampler_sha=digest(ROOT/'fakestormer_candidate.py'),limitations='Source IDs and target-gallery indices disjoint. Actor identity and upstream pretraining overlap unknown. Two face swaps only, no lip-sync.')
 path.write_text(json.dumps(config,indent=2),encoding='utf-8');return config

def features(rows,protocol):
 from backend.gend import load
 from fakestormer_candidate import read_clips
 assert digest(ROOT/'fakestormer_candidate.py')==protocol['sampler_sha']
 cache=ROOT/'runtime/ordered-video-features';cache.mkdir(exist_ok=True)
 key=hashlib.sha256((protocol['feature_protocol']+protocol['encoder_sha']+protocol['sampler_sha']).encode()).hexdigest()[:16]
 model=processor=device=None;out=[];rejected=[]
 try:
  for i,row in enumerate(rows):
   target=cache/(row['sha256']+'-'+key+'.npz')
   if not target.exists():
    if model is None:model,processor,device=load();model.requires_grad_(False)
    try:clips=read_clips(ROOT/row['path'])
    except ValueError as exc:rejected.append(dict(row,error=str(exc)));continue
    values=[];base=[];traces=[]
    for trace,x in clips:
     rgb=(x*torch.tensor([.229,.224,.225])[:,None,None,None]+torch.tensor([.485,.456,.406])[:,None,None,None]).permute(1,2,3,0).clamp(0,1)
     images=[Image.fromarray((frame.numpy()*255).round().astype('uint8')) for frame in rgb]
     tensors=processor(images=images,return_tensors='pt')['pixel_values'].to(device)
     with torch.inference_mode():
      feature=F.normalize(model.feature_extractor(tensors),dim=1);logits=model.model.linear(feature);values.append(feature.cpu().numpy().astype('float16'));base.append(float((logits[:,1]-logits[:,0]).mean()))
     traces.append(trace)
    temporary=target.with_suffix('.new')
    with temporary.open('wb') as stream:np.savez_compressed(stream,x=np.stack(values),base=np.array(base,dtype='float32'),traces=np.array(json.dumps(traces)))
    temporary.replace(target)
   with np.load(target,allow_pickle=False) as stored:
    x=stored['x'].astype('float32');base=stored['base'].astype('float32');traces=json.loads(str(stored['traces']))
   assert x.shape[1:]==(4,1024) and 1<=len(x)<=4 and np.isfinite(x).all() and np.isfinite(base).all()
   out.append((row,x,base,traces))
   if i%10==0:print('Ordered features',i+1,'/',len(rows),flush=True)
 finally:
  del model;gc.collect();torch.cuda.empty_cache()
 return out,rejected

def tensors(items,device):
 x=np.zeros((len(items),4,4,1024),dtype='float32');base=np.zeros((len(items),4),dtype='float32');mask=base.copy()
 for i,(_,value,raw,_) in enumerate(items):x[i,:len(value)]=value;base[i,:len(raw)]=raw;mask[i,:len(raw)]=1
 return tuple(torch.from_numpy(v).to(device) for v in (x,base,mask))

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['train','test'],default='train');parser.add_argument('--epochs',type=int,default=60);args=parser.parse_args();torch.set_num_threads(2)
 out=ROOT/'models/video-ordered-head';protocol=prepare();handle=acquire_training_lock(out);identity=digest(out/'data-protocol.json');device='cuda' if torch.cuda.is_available() else 'cpu'
 frozen=out/'frozen.json'
 if args.stage=='test' and not frozen.exists():raise RuntimeError('Complete training and freeze before testing')
 selected=[r for r in protocol['rows'] if (r['split']=='test')==(args.stage=='test')]
 items,rejected=features(selected,protocol);(out/('test-coverage.json' if args.stage=='test' else 'fit-coverage.json')).write_text(json.dumps(dict(planned=len(selected),usable=len(items),rejected=rejected),indent=2),encoding='utf-8')
 x,base,mask=tensors(items,device);y=torch.tensor([r[0]['label'] for r in items],dtype=torch.float32,device=device)
 torch.manual_seed(protocol['seed']);model=OrderedHead().to(device)
 from check_recent_model import statistics
 if args.stage=='test':
  config=json.loads(frozen.read_text());assert config['data_sha']==identity and config['code_sha']==digest(__file__);assert config['checkpoint_sha']==digest(out/'best.pt');model.load_state_dict(torch.load(out/'best.pt',weights_only=True,map_location=device)['head']);model.eval()
  with torch.inference_mode():scores=model(x,base,mask).sigmoid().cpu().tolist();shuffled=model(x,base,mask,order='shuffle').sigmoid().cpu().tolist();baseline=(base*mask).sum(1).div(mask.sum(1)).sigmoid().cpu().tolist()
  rows=[dict(item[0],score=s,predicted=int(s>=config['threshold']),baseline_score=b,shuffled_score=t,clips=item[3]) for item,s,b,t in zip(items,scores,baseline,shuffled)]
  report=dict(metrics=statistics(rows),same_frames_baseline=statistics([dict(r,predicted=int(r['baseline_score']>=.5)) for r in rows]),order_ablation_mean_delta=float(np.mean(np.abs(np.array(scores)-np.array(shuffled)))),results=rows,planned=len(selected),coverage=len(items)/len(selected),rejected=rejected,protocol=config,limitations=protocol['limitations'])
  (ROOT/'reports/ordered-temporal-head-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print({k:report[k] for k in ['metrics','same_frames_baseline','coverage','order_ablation_mean_delta']},flush=True);return
 if frozen.exists():print('Training already complete; use --stage test. Frozen model is never overwritten.');return
 opt=torch.optim.AdamW(model.parameters(),lr=protocol['lr'],weight_decay=.001);epoch=cursor=step=stale=0;best=1e10;history=[];stopped=False
 saved=load_latest(out/'last.pt')
 if saved:
  assert saved['manifest']==identity and saved['code_sha']==digest(__file__);model.load_state_dict(saved['head']);opt.load_state_dict(saved['optimizer']);epoch,cursor,step,best,stale,history=(saved[k] for k in ('epoch','cursor','step','best','stale','history'))
 def stop(*_):
  nonlocal stopped
  stopped=True
 signal.signal(signal.SIGINT,stop)
 def state():return dict(base='frozen-gend-ordered-gru-v1',manifest=identity,code_sha=digest(__file__),batch_size=16,head=model.state_dict(),optimizer=opt.state_dict(),epoch=epoch,cursor=cursor,step=step,best=best,stale=stale,history=history)
 train=torch.tensor([i for i,item in enumerate(items) if item[0]['split']=='train'],device=device);val=torch.tensor([i for i,item in enumerate(items) if item[0]['split']=='val'],device=device)
 positive=float(y[train].sum());weight=torch.tensor((len(train)-positive)/positive,device=device)
 while epoch<args.epochs and stale<protocol['patience'] and not stopped:
  order=train[torch.randperm(len(train),generator=torch.Generator().manual_seed(protocol['seed']+epoch)).to(device)]
  model.train()
  while cursor<len(order) and not stopped:
   ids=order[cursor:cursor+16];torch.manual_seed(protocol['seed']+step);opt.zero_grad();loss=F.binary_cross_entropy_with_logits(model(x[ids],base[ids],mask[ids]),y[ids],pos_weight=weight);loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.);opt.step();cursor+=len(ids);step+=1;save_checkpoint(state(),out/'last.pt')
  if stopped:break
  model.eval()
  with torch.inference_mode():logits=model(x[val],base[val],mask[val]);value=float(F.binary_cross_entropy_with_logits(logits,y[val]));scores=logits.sigmoid().cpu().tolist()
  metrics=statistics([dict(items[int(i)][0],score=s,predicted=int(s>=.5)) for i,s in zip(val.cpu(),scores)]);history.append(dict(epoch=epoch+1,validation_loss=value,metrics=metrics));print('Epoch',epoch+1,'validation BCE',value,metrics,flush=True)
  if value<best-1e-5:best=value;stale=0;save_checkpoint(dict(head=model.state_dict()),out/'best.pt')
  else:stale+=1
  epoch+=1;cursor=0;save_checkpoint(state(),out/'last.pt')
 if stopped:print('Saved; rerun the identical command to resume. No test predictions made.');return
 if epoch<protocol['epochs'] and stale<protocol['patience']:print('Requested segment complete; rerun with --epochs 60 to continue.');return
 model.load_state_dict(torch.load(out/'best.pt',weights_only=True,map_location=device)['head']);model.eval()
 with torch.inference_mode():scores=model(x[val],base[val],mask[val]).sigmoid().cpu().tolist()
 from evaluate_temporal_upgrade import best_threshold
 validation=[dict(items[int(i)][0],score=s) for i,s in zip(val.cpu(),scores)];threshold,metrics=best_threshold(validation,max_fpr=.05)
 config=dict(data_sha=identity,code_sha=digest(__file__),checkpoint_sha=digest(out/'best.pt'),threshold=threshold,validation_fit=metrics,history=history,scope=protocol['feature_protocol'],limitations=protocol['limitations'],auto_promote=False)
 frozen.write_text(json.dumps(config,indent=2),encoding='utf-8');(ROOT/'reports/ordered-temporal-head-training.json').write_text(json.dumps(config,indent=2),encoding='utf-8');print('Frozen before new source test',metrics,flush=True)
if __name__=='__main__':main()
