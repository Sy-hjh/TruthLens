import bootstrap
import json,time,hashlib,shutil,secrets,sys
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app
ROOT=Path(__file__).resolve().parent
out=ROOT/'submission';out.mkdir(exist_ok=True)
for name in ['av-real','av-fake']:
 shutil.copy2(ROOT.parent/'data/demo'/f'{name}.mp4',ROOT/'demo'/f'{name}.mp4')
rows=[]
with TestClient(app) as c:
 r=c.post('/api/auth/register',json={'username':'qa_'+secrets.token_hex(5),'password':secrets.token_urlsafe(20)})
 assert r.status_code==201,r.text
 for p in sorted((ROOT/'demo').iterdir()):
  if p.suffix.lower() not in {'.png','.wav','.m4a','.mp4'}:continue
  if '--images' in sys.argv and p.suffix.lower()!='.png':continue
  start=time.monotonic()
  with p.open('rb') as f:r=c.post('/api/analyze',files={'file':('sample'+p.suffix,f)},data={'scene':'general','context':''})
  assert r.status_code==202,r.text
  key=r.json()['job_id']
  while time.monotonic()-start<1200:
   job=c.get('/api/jobs/'+key).json()
   if job['status']!='processing':break
   time.sleep(1)
  row={'file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'seconds':round(time.monotonic()-start,2),'job':job}
  rows.append(row)
  (out/('image-retest-results.json' if '--images' in sys.argv else 'demo-test-results.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
  print(p.name,json.dumps(job,ensure_ascii=False)[:1800],flush=True)
