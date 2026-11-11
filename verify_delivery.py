"""Real-weight upload-to-report acceptance in an isolated report database."""
import bootstrap,json,time,tempfile,wave,io,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app import app
from backend import storage
from PIL import Image
ROOT=bootstrap.ROOT

def main():
 suite=unittest.defaultTestLoader.loadTestsFromNames(['tests','test_domain','test_advisor','test_checkpoint_io']);test_count=suite.countTestCases();outcome=unittest.TextTestRunner(verbosity=0).run(suite);assert outcome.wasSuccessful(),'Quick checks failed'
 checks=[]
 with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as tmp,patch.object(storage,'ROOT',Path(tmp)):
  client=TestClient(app)
  def submit(path,expected=(),failed=False):
   with Path(path).open('rb') as f:r=client.post('/api/analyze',files={'file':(Path(path).name,f)})
   assert r.status_code==202,r.text;key=r.json()['job_id'];start=time.monotonic()
   for _ in range(1600):
    result=client.get('/api/jobs/'+key).json()
    if result['status']!='processing':break
    time.sleep(.2)
   assert result['status']==('failed' if failed else 'completed'),result
   if not failed:
    for module in expected:assert result['result']['modules'][module]['status']=='completed',result
    assert client.get('/api/cases/'+key).status_code==200
    client.delete('/api/cases/'+key);assert client.get('/api/cases/'+key).status_code==404
   assert not list(Path(tmp).glob('upload-*')),'Raw upload left behind'
   checks.append(dict(name=Path(path).name,status=result['status'],seconds=round(time.monotonic()-start,2),modules={k:dict(status=v['status'],score=v.get('score'),source=v.get('source')) for k,v in result.get('result',{}).get('modules',{}).items()},phrases=len(result.get('result',{}).get('phrases',[]))))
   return result
  for name in ('family-simulation','normal-synthetic-control'):
   item=submit(ROOT/'data/demo'/(name+'.mp3'),['audio']);assert item['result']['transcript']['status']=='completed'
   if name=='family-simulation':assert item['result']['phrases']
   else:assert not item['result']['phrases']
  real=submit(ROOT/'data/chinese-human/0.wav',['audio']);assert max(s['score'] for s in real['result']['modules']['audio']['segments'])<.5,'Known real Mandarin unexpectedly flagged'
  for name in ('known-real','known-fake'):
   item=submit(ROOT/'data/demo'/(name+'.mp4'),['video']);assert item['result']['modules']['video']['source'].get('version'),'Website did not use versioned video release'
  image=Path(tmp)/'engineering-image.png';Image.new('RGB',(256,256),(70,120,140)).save(image);submit(image,['image'])
  broken=Path(tmp)/'broken.png';broken.write_bytes(b'not-an-image');submit(broken,failed=True)
  silent=Path(tmp)/'silent.wav'
  with wave.open(str(silent),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\0'*64000)
  item=submit(silent);assert item['result']['modules']['audio']['status']=='failed';assert 'score' not in item['result']['modules']['audio']
  assert client.get('/api/demo-video/not-a-file').status_code==404
  assert client.get('/models/active-audio.json').status_code==404
  assert client.post('/api/analyze',files={'file':('x.exe',b'no')}).status_code==415
  assert client.post('/api/analyze',files={'file':('x.wav',b'')}).status_code==422
  assert client.get('/#check').status_code==200
 report=dict(summary=f'{len(checks)}份材料链路检查通过（含预期失败）；{test_count}项自动规则/恢复检查通过。',checks=checks,raw_upload_cleanup=True,storage_isolated=True,scope='Engineering acceptance, not an accuracy benchmark. Browser native automation stopped because URL could not be reliably confirmed; desktop appearance, printing and actual mobile dialing remain user review items.')
 (ROOT/'reports/delivery-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report['summary'])
if __name__=='__main__':main()
