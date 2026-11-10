"""Fixed author checkpoint and threshold; no local fitting."""
import bootstrap,json,time
from pathlib import Path
from backend.sifta import load_handler,score
from check_recent_model import statistics
ROOT=bootstrap.ROOT

def main():
 rows=json.loads((ROOT/'data/video-release-check/manifest.json').read_text());handler=load_handler();results=[];rejected=[]
 for i,row in enumerate(rows):
  started=time.monotonic()
  try:r=score(handler,ROOT/row['path'])
  except ValueError as e:rejected.append(dict(row,reason=str(e)));continue
  results.append(dict(row,score=r['score'],predicted=int(r['score']>=r['threshold']),seconds=time.monotonic()-started))
  (ROOT/'reports/sifta-diagnostic-progress.json').write_text(json.dumps(dict(results=results,rejected=rejected),indent=2))
  if i%10==0:print('SIFTA cross-source diagnostic',i+1,'/',len(rows),flush=True)
 report=dict(metrics=statistics(results),results=results,rejected=rejected,planned=len(rows),threshold=handler.threshold,temperature=handler.T,note='Fixed author model/validation threshold, same200 previously observed RTFS diagnostic clips. No local training, unknown upstream pretraining overlap. Further source check required before release.')
 (ROOT/'reports/sifta-diagnostic.json').write_text(json.dumps(report,indent=2));print(report['metrics'])
if __name__=='__main__':main()
