"""Validate then freeze a spatial+true-temporal calibration layer before new-source test.
No encoder training. Nonnegative 2-input logistic calibration; L2=.1 fixed.
"""
import bootstrap,argparse,json,hashlib,time,math
from pathlib import Path
import numpy as np
from check_recent_model import statistics
ROOT=bootstrap.ROOT
def identity():
 files=['fakestormer_candidate.py','ftcn_candidate.py','backend/gend.py','backend/faces.py','backend/media.py']
 return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in files}
def logit(p):p=np.clip(p,1e-5,1-1e-5);return np.log(p/(1-p))
def fused(a,b,c):return float(1/(1+np.exp(-np.clip(c[0]*logit(a)+c[1]*logit(b)+c[2],-30,30))))
def best_threshold(rows,max_fpr=.04):
 candidates=[1.000001]+sorted({r['score'] for r in rows});best=None
 for threshold in candidates:
  metrics=statistics([dict(r,predicted=int(r['score']>=threshold)) for r in rows])
  if metrics['real_false_positive_rate']>max_fpr:continue
  rank=(metrics['balanced_accuracy'],threshold)
  if best is None or rank>best[0]:best=(rank,threshold,metrics)
 return best[1:]
def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',choices=['temporal-validation','spatial-validation','freeze','temporal-test','spatial-test','report'],required=True);a=p.parse_args();folder=ROOT/'models/video-spatiotemporal';folder.mkdir(exist_ok=True);protocol=folder/'frozen-protocol.json'
 if a.stage=='freeze':
  left=json.loads((ROOT/'reports/spatial-validation-new50.json').read_text(encoding='utf-8'));right={r['path']:r for r in json.loads((ROOT/'reports/temporal-validation-new50.json').read_text(encoding='utf-8')) if 'score' in r};paired=[dict(r,temporal=right[r['path']]['score']) for r in left if 'score' in r and r['path'] in right];x=np.asarray([[logit(r['score']),logit(r['temporal'])] for r in paired]);y=np.asarray([r['label'] for r in paired])
  from scipy.optimize import minimize
  objective=lambda c:float(np.mean(np.logaddexp(0,x@c[:2]+c[2])-y*(x@c[:2]+c[2]))+.1*np.sum(c[:2]**2))
  result=minimize(objective,np.array([.5,.5,0.]),bounds=[(0,None),(0,None),(None,None)],method='L-BFGS-B');assert result.success;coef=result.x.tolist();calibrated=[dict(r,score=fused(r['score'],r['temporal'],coef)) for r in paired];threshold,metrics=best_threshold(calibrated);temporal_threshold,temporal_metrics=best_threshold([dict(r,score=r['temporal']) for r in paired])
  value=dict(engine='gend-fakestormer',code_sha256=identity(),weights=dict(gend=json.loads((ROOT/'models/gend-clip/source.json').read_text())['sha256'],fakestormer=json.loads((ROOT/'models/fakestormer/source.json').read_text())['sha256']),coefficients=coef,threshold=threshold,temporal_review_threshold=temporal_threshold,calibration_fit=metrics,temporal_calibration_fit=temporal_metrics,calibration_n=len(paired),objective='nonnegative two-logit logistic calibration, fixed L2=.1; threshold max balanced accuracy with validation real FPR<=4%; highest threshold breaks ties',scope='Fitted on old validation source groups, not independent accuracy. Encoders frozen; not fraud probability. New source20groups never used here.',temporal_protocol='Up to4clips, each four ordered frames [0,10,21,31] from32consecutive-frame face spans; spatial+temporal attention, not lip-sync')
  if protocol.exists() and json.loads(protocol.read_text(encoding='utf-8'))!=value:raise RuntimeError('Protocol frozen: changed model requires a new test cohort/output version')
  protocol.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');print('Frozen before new-source predictions',value,flush=True);return
 if a.stage=='report':
  config=json.loads(protocol.read_text(encoding='utf-8'));assert config['code_sha256']==identity();spatial=json.loads((ROOT/'reports/spatial-test-new.json').read_text(encoding='utf-8'));temporal={r['path']:r for r in json.loads((ROOT/'reports/temporal-test-new.json').read_text(encoding='utf-8'))};out=[];rejected=[]
  for row in spatial:
   other=temporal.get(row['path'])
   if 'score' not in row or not other or 'score' not in other:rejected.append(dict(path=row['path'],reason='Missing usable spatial or temporal evidence'));continue
   value=fused(row['score'],other['score'],config['coefficients']);out.append(dict(row,spatial_score=row['score'],temporal_score=other['score'],score=value,predicted=int(value>=config['threshold']),temporal_clips=other['clips']))
  report=dict(protocol=config,metrics=statistics(out),spatial_same_usable=statistics([dict(r,score=r['spatial_score'],predicted=int(r['spatial_score']>=.5)) for r in out]),temporal_author_threshold=statistics([dict(r,predicted=int(r['temporal_score']>=.5)) for r in out]),temporal_calibrated_threshold=statistics([dict(r,predicted=int(r['temporal_score']>=config['temporal_review_threshold'])) for r in out]),planned=60,usable=len(out),coverage=len(out)/60,rejected=rejected,results=out,limitations=['20 locally new source video IDs; actor identity and upstream pretraining overlap unknown.','Two face-swap generators, not all whole-generated or GPT/Sora videos.','Calibration50old clips is model fitting, not test performance; no temporal encoder retraining.','YuNet face preprocessing adaptation differs from original landmark-cropped paper data.'])
  report['by_generator']={g:statistics([r for r in out if r['label']==0 or r['generator']==g]) for g in ['inswapper','uniface']};(ROOT/'reports/spatiotemporal-upgrade-test.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print({k:report[k] for k in ['metrics','spatial_same_usable','temporal_author_threshold','temporal_calibrated_threshold','coverage']},flush=True);return
 engine,phase=a.stage.split('-',1);is_test=phase=='test'
 if is_test:
  config=json.loads(protocol.read_text(encoding='utf-8'));assert config['code_sha256']==identity(),'Frozen inference changed after calibration'
 rows=json.loads((ROOT/'data/video-temporal-check/manifest.json').read_text(encoding='utf-8')) if is_test else json.loads((ROOT/'reports/sifta-calibration.json').read_text(encoding='utf-8'))['results'];progress=ROOT/f'reports/{a.stage}-new{"" if is_test else "50"}.json';out=json.loads(progress.read_text(encoding='utf-8')) if progress.exists() else [];done={r['path'] for r in out}
 import torch
 torch.set_num_threads(2)
 if engine=='temporal':
  from fakestormer_candidate import load,predict
  model=load();scorer=lambda path:predict(model,path)
 else:
  from backend.gend import load,score
  model,processor,device=load();scorer=lambda path:dict(score=score(model,processor,device,path))
 for i,row in enumerate(rows):
  if row['path'] in done:continue
  started=time.monotonic()
  try:
   result=scorer(ROOT/row['path']);value=float(result['score']);assert math.isfinite(value) and 0<=value<=1;out.append(dict(row,**result,seconds=time.monotonic()-started))
  except ValueError as exc:out.append(dict(row,error=str(exc)))
  temp=progress.with_suffix('.new');temp.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(progress)
  if i%5==0:print(a.stage,i+1,'/',len(rows),flush=True)
 print('Stage complete',a.stage,len(out),flush=True)
if __name__=='__main__':main()
