"""Real HTTP/offline parity and upload-cache privacy; not a new accuracy estimate."""
import bootstrap,json,time,math,requests
from bootstrap import ROOT
BASE='http://127.0.0.1:8010'
def main():
 rows=json.loads((ROOT/'reports/ordered-temporal-head-test.json').read_text())['results'][:2]
 rows+= [dict(path='data/demo/known-real-2.mp4',label=0)]
 before={p.name for p in (ROOT/'runtime/ordered-video-features').glob('*.npz')};out=[]
 for i,row in enumerate(rows):
  with (ROOT/row['path']).open('rb') as stream:response=requests.post(BASE+'/api/analyze',files={'file':(f'qa-ordered-parity-{i}.mp4',stream,'video/mp4')},timeout=20)
  response.raise_for_status();key=response.json()['job_id']
  try:
   for _ in range(300):
    job=requests.get(BASE+'/api/jobs/'+key,timeout=10).json()
    if job['status']!='processing':break
    time.sleep(.3)
   assert job['status']=='completed',job
   value=job['result']['modules']['video'];assert value['status']=='completed' and value['method']=='temporal-sequence',value
   assert math.isfinite(value['score']) and all(len(r['frame_indices'])==4 for r in value['moments'])
   delta=abs(value['score']-row['score']) if 'score' in row else None
   if delta is not None:assert delta<1e-5,(value,row)
   out.append(dict(path=row['path'],label=row['label'],score=value['score'],threshold=value['threshold'],correct=int(value['score']>=value['threshold'])==row['label'],offline_absolute_difference=delta,clips=len(value['moments'])))
  finally:requests.delete(BASE+'/api/cases/'+key,timeout=10).raise_for_status()
 after={p.name for p in (ROOT/'runtime/ordered-video-features').glob('*.npz')};assert before==after,'Uploads must not enter public feature cache'
 report=dict(actual_http=True,model='qinan-ordered-gru-r1-20261112',no_upload_feature_cache=True,disposable_cases_removed=True,checks=out,scope='Fixed first2 held-out rows and public real fixture; parity/regression only, not new accuracy.')
 (ROOT/'reports/ordered-delivery-parity.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(report,flush=True)
if __name__=='__main__':main()
