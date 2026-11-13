"""Live HTTP: public audible video -> unchanged three checks -> LangChain SSE -> deletion."""
import bootstrap,json,time,requests
from bootstrap import ROOT
BASE='http://127.0.0.1:8010'

def main():
 out={'fixture':'FakeAVCeleb public author av-fake.mp4; not user media'};key=None
 try:
  r=requests.get(BASE+'/api/agent/capabilities',timeout=15);r.raise_for_status();out['capabilities']=r.json()
  assert all(out['capabilities']['framework'].values())
  with (ROOT/'data/demo/av-fake.mp4').open('rb') as f:r=requests.post(BASE+'/api/analyze',files={'file':('agent-public-av-fake.mp4',f,'video/mp4')},timeout=30)
  r.raise_for_status();key=r.json()['job_id'];start=time.monotonic()
  while time.monotonic()-start<360:
   job=requests.get(BASE+'/api/jobs/'+key,timeout=15).json()
   if job['status']!='processing':break
   time.sleep(.3)
  assert job['status']=='completed',job
  result=job['result'];out['media_result']=result
  for modality in ['video','audio']:assert result['modules'][modality]['status']=='completed'
  assert result['transcript']['status']=='completed';assert result['speech_analysis']['status']=='completed'
  print('Public video: visual, acoustic, transcript/content all completed',flush=True)
  events=[]
  with requests.post(BASE+f'/api/cases/{key}/agent-events',json={'question':'这段声音和画面能证明是我的家人吗，我应该怎么核实？'},stream=True,timeout=(10,180)) as r:
   r.raise_for_status();r.encoding='utf-8'
   for line in r.iter_lines(decode_unicode=True):
    if line.startswith('data: '):
     event=json.loads(line[6:]);events.append(event);print(event.get('type'),event.get('tool'),event.get('status'),flush=True)
  out['events']=events;final=events[-1]['result'];assert final['mode']=='langchain_agent',final
  assert {'read_report','search_guidance'}<={t['tool'] for t in final['trace']}
  print('Actual LangChain SSE and citations passed',flush=True)
  r=requests.post(BASE+f'/api/cases/{key}/feedback',json={'verdict':'useful'},timeout=15);r.raise_for_status();out['feedback']=r.json();assert not out['feedback']['used_for_training']
 finally:
  if key:
   r=requests.delete(BASE+'/api/cases/'+key,timeout=15);r.raise_for_status();out['deleted']=requests.get(BASE+'/api/cases/'+key,timeout=15).status_code==404
  (ROOT/'reports/agent-http-acceptance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
