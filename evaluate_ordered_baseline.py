"""Active eight-frame model on the new ordered-head cohort; fixed threshold .5."""
import bootstrap,json,time
import torch
from bootstrap import ROOT
def main():
 from backend.gend import load,score
 torch.set_num_threads(2);model,processor,device=load();rows=json.loads((ROOT/'data/video-temporal-head-test/manifest.json').read_text());path=ROOT/'reports/ordered-head-active-baseline.json';out=json.loads(path.read_text())['results'] if path.exists() else [];done={r['path'] for r in out}
 from check_recent_model import statistics
 for i,row in enumerate(rows):
  if row['path'] in done:continue
  try:
   value=score(model,processor,device,ROOT/row['path']);out.append(dict(row,score=value,predicted=int(value>=.5)))
  except ValueError as exc:out.append(dict(row,error=str(exc)))
  usable=[r for r in out if 'score' in r];report=dict(metrics=statistics(usable),coverage=len(usable)/len(rows),results=out,scope='Frozen active GenD author.5; same new cohort as ordered head, no fitting.');temporary=path.with_suffix('.new');temporary.write_text(json.dumps(report,indent=2),encoding='utf-8');temporary.replace(path)
  if i%10==0:print('Active baseline',i+1,'/',len(rows),flush=True)
 print(report['metrics'],flush=True)
if __name__=='__main__':main()
