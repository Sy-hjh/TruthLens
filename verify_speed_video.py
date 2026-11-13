"""Full pipeline cold/warm timings; store result before assertions for auditing."""
import bootstrap,json,time,requests
from pathlib import Path
from bootstrap import ROOT
BASE='http://127.0.0.1:8010'
def main():
 out=[]
 for i in range(2):
  path=ROOT/'data/demo/av-real.mp4';started=time.monotonic()
  with path.open('rb') as stream:r=requests.post(BASE+'/api/analyze',files={'file':('speed-real-with-audio.mp4',stream,'video/mp4')},timeout=20)
  r.raise_for_status();key=r.json()['job_id']
  try:
   for _ in range(1200):
    job=requests.get(BASE+'/api/jobs/'+key,timeout=15).json()
    if job['status']!='processing':break
    time.sleep(.3)
   out.append(dict(run=i+1,wall_seconds=time.monotonic()-started,job=job));(ROOT/'reports/video-speed-full.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
   assert job['status']=='completed',job
   report=job['result']
   for kind in ['video','audio']:assert report['modules'][kind]['status']=='completed',report['modules'][kind]
   assert report['audio_info']['status']=='available',report['audio_info'];assert report['transcript']['status']=='completed',report['transcript'];assert report['speech_analysis']['status']=='completed',report['speech_analysis']
   print(i+1,out[-1]['wall_seconds'],report['timings'],flush=True)
  finally:requests.delete(BASE+'/api/cases/'+key,timeout=15).raise_for_status()
 print('Both full three-branch video checks completed',flush=True)
if __name__=='__main__':main()
