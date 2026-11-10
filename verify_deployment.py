"""TCP deployment check against the running local server, using a public disposable fixture."""
import bootstrap,requests,time,json
from pathlib import Path
ROOT=bootstrap.ROOT;BASE='http://127.0.0.1:8010'
def main():
 health=requests.get(BASE+'/api/health',timeout=10);health.raise_for_status();assert health.json()['version']=='3.0.0'
 statuses={}
 for path in (ROOT/'frontend-next/assets').iterdir():
  if path.suffix not in ('.js','.css'):continue
  r=requests.get(BASE+'/assets/'+path.name,timeout=10);assert r.status_code==200;assert not r.headers['Content-Type'].startswith('text/html');statuses[path.name]=r.status_code
 evidence=requests.get(BASE+'/api/evidence',timeout=10).json();expected=json.loads((ROOT/'models/active-video.json').read_text())['version'];assert evidence['releases']['video']==expected
 with (ROOT/'data/demo/known-fake-2.mp4').open('rb') as f:r=requests.post(BASE+'/api/analyze',files={'file':('qa-public-face-swap-2.mp4',f,'video/mp4')},timeout=20)
 r.raise_for_status();key=r.json()['job_id'];started=time.monotonic()
 for _ in range(600):
  job=requests.get(BASE+'/api/jobs/'+key,timeout=10).json()
  if job['status']!='processing':break
  time.sleep(.5)
 assert job['status']=='completed',job;video=job['result']['modules']['video'];assert video['status']=='completed',video;assert video['source']['version']==expected,video;assert video['score']>=video['threshold'],'Known paired positive regression missed'
 report=dict(health=health.json(),assets=statuses,video=video,seconds=round(time.monotonic()-started,2),actual_http=True,disposable_report_removed=True)
 requests.delete(BASE+'/api/cases/'+key,timeout=10).raise_for_status();assert requests.get(BASE+'/api/cases/'+key,timeout=10).status_code==404;assert requests.get(BASE+'/api/jobs/'+key,timeout=10).status_code==404
 (ROOT/'reports/deployment-http.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print('Actual TCP deployment passed; served',expected,'score',video['score'])
if __name__=='__main__':main()
