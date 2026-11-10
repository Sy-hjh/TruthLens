"""Frozen protocol, evaluated once on the300fresh-source clips. No tuning."""
import bootstrap,json,hashlib,time
from pathlib import Path
from backend.video_fusion import Bundle
from check_recent_model import statistics
ROOT=bootstrap.ROOT

def main():
 calibration=json.loads((ROOT/'models/video-face-adapt/fusion-calibration.json').read_text());head=ROOT/'models/video-face-adapt/best-head.pt';config=dict(coefficients=calibration['coefficients'],threshold=.5,head=head.relative_to(ROOT).as_posix(),head_sha256=hashlib.sha256(head.read_bytes()).hexdigest(),engine='video-fusion')
 protocol=ROOT/'data/video-final/frozen-predictor.json'
 if protocol.exists():assert json.loads(protocol.read_text())==config,'Frozen predictor changed after test protocol'
 else:protocol.write_text(json.dumps(config,indent=2))
 rows=json.loads((ROOT/'data/video-final/manifest.json').read_text());used=[]
 for f in ['data/video-fit/manifest.json','data/video-release-check/manifest.json']:used.extend(json.loads((ROOT/f).read_text()))
 identity=lambda r:Path(r['group']).stem.rsplit('_',2)[0]
 assert not {identity(r) for r in rows}&{identity(r) for r in used},'Source ID overlap'
 assert len({identity(r) for r in rows})==100
 assert not {r['sha256'] for r in rows}&{r['sha256'] for r in used},'Byte-identical content overlap'
 bundle=Bundle(config);progress=ROOT/'reports/video-final-progress.json';saved=json.loads(progress.read_text()) if progress.exists() else {};results=saved.get('results',[]);rejected=saved.get('rejected',[]);done={r['remote'] for r in results+rejected}
 for i,row in enumerate(rows):
  if row['remote'] in done:continue
  started=time.monotonic()
  try:value=bundle.predict(ROOT/row['path'])
  except ValueError as exc:rejected.append(dict(row,reason=str(exc)));continue
  results.append(dict(row,score=value['score'],predicted=int(value['score']>=.5),detector_scores=value['detector_scores'],seconds=time.monotonic()-started))
  (ROOT/'reports/video-final-progress.json').write_text(json.dumps(dict(results=results,rejected=rejected),indent=2))
  if i%10==0:print('Fresh final test',i+1,'/',len(rows),flush=True)
 report=dict(metrics=statistics(results),planned=len(rows),processed=len(results),coverage=len(results)/len(rows),rejected=rejected,by_generator={g:statistics([r for r in results if r['generator']==g or r['label']==0]) for g in ('inswapper','uniface')},results=results,predictor=config,note='100newsource YouTube IDs excluded from local train, calibration and observed diagnostics; two face-swap generators. Actor identity separation and pretraining overlap not verified. Threshold and calibration coefficients frozen before this test. This is a small research benchmark, not elderly-domain or all-generated-video accuracy.')
 (ROOT/'reports/video-final-evaluation.json').write_text(json.dumps(report,indent=2));print(report['metrics']);print('Coverage',report['coverage'])
if __name__=='__main__':main()
