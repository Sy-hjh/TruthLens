"""Auditable follow-up temporal baseline, never auto-activates an inferior model."""
import bootstrap,json,time,hashlib
import torch
from ftcn_candidate import load,predict,clips
from check_recent_model import statistics
ROOT=bootstrap.ROOT
def main():
 torch.set_num_threads(2)
 for attempt in range(150):
  if (ROOT/'models/ftcn/source.json').exists():break
  if attempt%15==0:print('Waiting for official temporal weight download',flush=True)
  time.sleep(2)
 else:raise RuntimeError('Temporal weight download incomplete; no result invented.')
 model=load();rows=json.loads((ROOT/'data/video-gend-final/manifest.json').read_text(encoding='utf-8'))
 groups=sorted({r['group'] for r in rows},key=lambda s:hashlib.sha256(s.encode()).hexdigest())[:12];rows=[r for r in rows if r['group'] in groups]
 progress=ROOT/'reports/ftcn-contiguous-comparison.partial.json';saved=json.loads(progress.read_text()) if progress.exists() else dict(results=[],rejected=[]);done={r['path'] for r in saved['results']+saved['rejected']}
 for i,row in enumerate(rows):
  if row['path'] in done:continue
  try:result=predict(model,ROOT/row['path'])
  except ValueError as exc:saved['rejected'].append(dict(row,reason=str(exc)))
  else:saved['results'].append(dict(row,score=result['score'],predicted=int(result['score']>=.5),clips=result['clips']))
  progress.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8');print(i+1,'/',len(rows),flush=True)
 probes=[]
 for label in [0,1]:
  row=next((r for r in saved['results'] if r['label']==label),None)
  if row is None:continue
  trace,x=clips(ROOT/row['path'],limit=1)[0];device=next(model.parameters()).device;values={}
  for variant,indices in [('original',torch.arange(32)),('reverse',torch.arange(31,-1,-1)),('shuffle',torch.randperm(32,generator=torch.Generator().manual_seed(714))),('repeated_first',torch.zeros(32,dtype=torch.long))]:
   with torch.inference_mode():values[variant]=float(model(x[:,indices].unsqueeze(0).to(device))['final_output'].view(-1)[0])
  probes.append(dict(sha256=row['sha256'],label=label,scores=values,scope='Artificial order control, not deepfake accuracy or localized evidence'))
 reference=json.loads((ROOT/'reports/gend-final.json').read_text(encoding='utf-8'))['fresh180']['results'];lookup={r['path']:r for r in reference};matched=[r for r in saved['results'] if r['path'] in lookup]
 report=dict(engine='FTCN+TT, author2021',frames='Four distributed clips, each32consecutive native-fps frames; gaps between clips not analyzed.',preprocessing='Local YuNet same-person nearest-center check with constant union box, not author original landmark alignment. This adapted pipeline may differ in performance.',metrics=statistics(saved['results']),gend_on_same_usable_files=statistics([lookup[r['path']] for r in matched]),planned=len(rows),rejected=len(saved['rejected']),coverage=len(saved['results'])/len(rows),order_probes=probes,scope='Fixed SHA-selected12source groups from previously observed test. Follow-up diagnostic, not new independent accuracy. No threshold tuning.',activated=False,results=saved['results'],rejected_rows=saved['rejected'])
 (ROOT/'reports/ftcn-contiguous-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ['metrics','gend_on_same_usable_files','coverage','order_probes']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
