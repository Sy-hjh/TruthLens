"""Calibrate only on pre-existing validation source groups, never the diagnostic clips."""
import bootstrap,json,hashlib
from pathlib import Path
from backend.sifta import load_handler,score
from check_recent_model import statistics
ROOT=bootstrap.ROOT

def main():
 rows=[r for r in json.loads((ROOT/'data/video-fit/manifest.json').read_text()) if r['split']=='val'];handler=load_handler();results=[];rejected=[]
 for i,row in enumerate(rows):
  try:r=score(handler,ROOT/row['path'])
  except ValueError as e:rejected.append(dict(row,reason=str(e)));continue
  results.append(dict(row,score=r['score'],predicted=int(r['score']>=r['threshold'])))
  print('Validation only calibration',i+1,'/',len(rows),flush=True)
 candidates=sorted({0.,1.,*[r['score'] for r in results],*[min(1.,r['score']+1e-7) for r in results]});options=[]
 for threshold in candidates:
  metric=statistics([dict(r,predicted=int(r['score']>=threshold)) for r in results])
  if metric['real_false_positive_rate']<=.04:options.append((metric['balanced_accuracy'],threshold,metric))
 _,threshold,metric=max(options);source=json.loads((ROOT/'models/sifta/source.json').read_text());report=dict(threshold=threshold,validation=metric,results=results,rejected=rejected,weights_sha256=source['sha256'],protocol='25 held-out validation source IDs, real+inswapper, fixed author model and temperature. Maximize balanced accuracy subject to real FPR<=4%. Largest threshold breaks ties. Does not use the200 diagnostic source IDs. Next fresh source test must not adjust this threshold.')
 (ROOT/'models/sifta/local-calibration.json').write_text(json.dumps(report,indent=2));print('Calibration result',threshold,metric)
 diagnostic=json.loads((ROOT/'reports/sifta-diagnostic.json').read_text());report['observed_diagnostic']=statistics([dict(r,predicted=int(r['score']>=threshold)) for r in diagnostic['results']]);(ROOT/'reports/sifta-calibration.json').write_text(json.dumps(report,indent=2));print('Previously observed diagnostic',report['observed_diagnostic'])
if __name__=='__main__':main()
