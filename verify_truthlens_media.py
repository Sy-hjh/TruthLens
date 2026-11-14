"""Eight pre-existing, labelled QA fixtures. Not an independent accuracy benchmark."""
import bootstrap,json,time,requests,mimetypes
from bootstrap import ROOT
BASE='http://127.0.0.1:8010'
def is_alert(module):
 if module.get('status')!='completed':return None
 values=[(s['score'],s.get('threshold',.5)) for s in module.get('segments',[])]
 if module.get('score') is not None:values.append((module['score'],module.get('threshold',.5)))
 return any(s>=t for s,t in values) if values else None
def main():
 rows=json.loads((ROOT/'reports/eight-demo-manifest.json').read_text(encoding='utf-8'));checks=[];out=ROOT/'reports/truthlens-eight-media-check.json'
 for i,item in enumerate(rows):
  path=ROOT/'演示素材_八个'/item['file'];kind=item['kind'];key=None;start=time.monotonic()
  try:
   with path.open('rb') as f:r=requests.post(BASE+'/api/analyze',files={'file':(f'verification-{i+1:02d}'+path.suffix,f,mimetypes.guess_type(path.name)[0] or 'application/octet-stream')},data={'scene':'chat' if kind=='chat' else 'general','context':'__truthlens_qa__eight-media-regression'},timeout=30)
   r.raise_for_status();key=r.json()['job_id']
   while time.monotonic()-start<600:
    job=requests.get(BASE+'/api/jobs/'+key,timeout=20).json()
    if job['status']!='processing':break
    time.sleep(.5)
   assert job['status']=='completed',job
   report=job['result'];module=report.get('modules',{}).get(kind,{})
   actual=report.get('chat_analysis',{}).get('assessment',{}).get('level') in {'alert','attention'} if kind=='chat' else is_alert(module)
   check=dict(fixture=item['file'],kind=kind,expected=item['expected_alert'],actual=actual,passed=actual==item['expected_alert'],seconds=round(time.monotonic()-start,2),modules=report.get('modules'),content=report.get('chat_analysis') if kind=='chat' else report.get('speech_analysis'),transcript=report.get('transcript'))
   if kind=='video':check['three_branches_completed']=report['modules']['audio']['status']=='completed' and report['transcript']['status']=='completed' and report['speech_analysis']['status']=='completed';check['passed']=check['passed'] and check['three_branches_completed']
   checks.append(check);print(json.dumps({k:check[k] for k in ('fixture','kind','passed','seconds')},ensure_ascii=False),flush=True)
  finally:
   if key:requests.delete(BASE+'/api/cases/'+key,timeout=20).raise_for_status()
   out.write_text(json.dumps({'scope':'8 curated regression fixtures used previously; not novel generators or general accuracy; labels never supplied to detector','checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
 assert len(checks)==8 and all(c['passed'] for c in checks),'Some fixtures failed; preserve evidence rather than change labels/thresholds'
if __name__=='__main__':main()
