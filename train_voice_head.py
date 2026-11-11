"""Resumable classifier-only training on speaker-disjoint genuine/cloned Mandarin."""
import bootstrap,json,argparse,time,hashlib,signal
import numpy as np,torch
from voice_features import ROOT,cache_path
from voice_head import make_head
from checkpoint_io import load_latest,save_checkpoint,acquire_training_lock
def main():
 p=argparse.ArgumentParser();p.add_argument('--epochs',type=int,default=80);p.add_argument('--patience',type=int,default=10);p.add_argument('--batch-size',type=int,default=128);p.add_argument('--output',default='models/voice-clone-v1');p.add_argument('--wait',action='store_true');p.add_argument('--max-steps',type=int,default=0);a=p.parse_args();torch.set_num_threads(2);torch.manual_seed(615)
 stopped=False
 def stop(*_):
  nonlocal stopped
  stopped=True;print('Stop requested; saving after current update',flush=True)
 signal.signal(signal.SIGINT,stop)
 if hasattr(signal,'SIGBREAK'):signal.signal(signal.SIGBREAK,stop)
 last_log=0
 while not stopped:
  manifest=ROOT/'data/clone-bench/manifest-audited.json';rows=json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
  selected=[r for r in rows if r['split'] in ('train','val')];missing=sum(not cache_path(r).exists() for r in selected)
  if rows and not missing:break
  if not a.wait:raise RuntimeError('Run collect_clone_bench.py and extract_voice_features.py first')
  if time.monotonic()-last_log>30:print('Waiting for complete training/validation acoustic features; test speakers excluded',missing,flush=True);last_log=time.monotonic()
  time.sleep(2)
 if stopped:return
 speakers={s:{r['speaker'] for r in rows if r['split']==s} for s in ('train','val','test')}
 assert not speakers['train']&speakers['val'] and not speakers['train']&speakers['test'] and not speakers['val']&speakers['test']
 data={}
 for split in ('train','val'):
  subset=[r for r in selected if r['split']==split];xs=[];ys=[];variants=[]
  for r in subset:
   x=np.load(cache_path(r));xs.extend(x);ys.extend([r['label']]*len(x));variants.extend(range(len(x)))
  data[split]=(torch.tensor(np.asarray(xs),dtype=torch.float32),torch.tensor(ys,dtype=torch.float32),torch.tensor(variants))
 x,y,_=data['train'];vx,vy,vi=data['val'];head=make_head(x.shape[1]);optimizer=torch.optim.AdamW(head.parameters(),lr=.0003,weight_decay=.01)
 base_sha=json.loads((ROOT/'models/audio-forensics/source.json').read_text())['sha256'];identity=hashlib.sha256(json.dumps([{k:r[k] for k in ('path','sha256','label','speaker','split')} for r in selected],sort_keys=True).encode()+base_sha.encode()+b'frozen-aasist-clean-aac32-phone8-head64-v1').hexdigest();folder=ROOT/a.output;folder.mkdir(parents=True,exist_ok=True);lock=acquire_training_lock(folder);checkpoint=folder/'last.pt'
 epoch=cursor=step=stale=0;best=-1.;best_loss=float('inf');saved=load_latest(checkpoint)
 if saved:
  if saved['identity']!=identity or saved['batch_size']!=a.batch_size:raise RuntimeError('Data/preprocessing changed; use a separate --output directory')
  head.load_state_dict(saved['head']);optimizer.load_state_dict(saved['optimizer']);epoch,cursor,step,stale,best,best_loss=[saved[k] for k in ('epoch','cursor','step','stale','best','best_loss')];print('Resuming',epoch,cursor,step,flush=True)
 weights=torch.where(y==1,len(y)/(2*(y==1).sum()),len(y)/(2*(y==0).sum()))
 def save():save_checkpoint(dict(base='xlsr-aasist-frozen-v1',manifest=identity,identity=identity,batch_size=a.batch_size,head=head.state_dict(),optimizer=optimizer.state_dict(),epoch=epoch,cursor=cursor,step=step,stale=stale,best=best,best_loss=best_loss),checkpoint)
 history=json.loads((folder/'history.json').read_text()) if (folder/'history.json').exists() else [];updates=0
 if saved and a.patience and stale>=a.patience:
  print('This run already stopped for validation stagnation. Raise --patience or use --patience 0 only for a deliberate new continuation.',flush=True);return
 while epoch<a.epochs and not stopped:
  order=torch.randperm(len(y),generator=torch.Generator().manual_seed(615+epoch))
  head.train()
  while cursor<len(order) and not stopped:
   ids=order[cursor:cursor+a.batch_size];optimizer.zero_grad(set_to_none=True);loss=torch.nn.functional.binary_cross_entropy_with_logits(head(x[ids]).squeeze(-1),y[ids],weight=weights[ids]);loss.backward();optimizer.step();cursor+=len(ids);step+=1;updates+=1;save()
   if (folder/'STOP').exists() or (a.max_steps and updates>=a.max_steps):stopped=True
  if cursor==len(order):
   head.eval()
   with torch.inference_mode():
    logits=head(vx).squeeze(-1);pred=logits>=0;variant_scores=[]
    for kind in range(3):
     mask=vi==kind;real=mask&(vy==0);fake=mask&(vy==1);variant_scores.append(float(((~pred[real]).float().mean()+pred[fake].float().mean())/2))
    weighted=torch.where(vy==1,len(vy)/(2*(vy==1).sum()),len(vy)/(2*(vy==0).sum()));vl=float(torch.nn.functional.binary_cross_entropy_with_logits(logits,vy,weight=weighted));score=min(variant_scores)
   if score>best or (score==best and vl<best_loss):
    best=score;best_loss=vl;stale=0;save_checkpoint(dict(head=head.state_dict(),identity=identity,dim=x.shape[1],epoch=epoch+1),folder/'best.pt')
   else:stale+=1
   history.append(dict(epoch=epoch+1,step=step,validation_balanced_accuracy_by_channel=variant_scores,worst_channel_balanced_accuracy=score,val_balanced_loss=vl,stale=stale));(folder/'history.json').write_text(json.dumps(history,indent=2));print(history[-1],flush=True);epoch+=1;cursor=0;save()
   if a.patience and stale>=a.patience:print('Early stopping; best head retained',flush=True);break
 save();print('Saved resumable acoustic classifier:',folder,'best validation worst-channel',best,flush=True)
if __name__=='__main__':main()
