"""Actual upload dual checks; fixed engineering controls, not accuracy benchmark."""
import bootstrap,json,time,copy,requests
from pathlib import Path
from bootstrap import ROOT
BASE='http://127.0.0.1:8010'
def main():
 out=[]
 for relative,kind,risk,keep in [('data/speech-dual-check/fictional-borrowing.mp3','audio',True,True),('data/demo/normal-synthetic-control.mp3','audio',False,False),('data/demo/av-real.mp4','video',False,False)]:
  path=ROOT/relative
  with path.open('rb') as stream:r=requests.post(BASE+'/api/analyze',files={'file':(path.name,stream)},timeout=30)
  r.raise_for_status();key=r.json()['job_id']
  try:
   for _ in range(900):
    job=requests.get(BASE+'/api/jobs/'+key,timeout=15).json()
    if job['status']!='processing':break
    time.sleep(.5)
   assert job['status']=='completed',job
   report=job['result'];assert report['modules'][kind]['status']=='completed'
   assert report['transcript']['status']=='completed' and report['transcript']['text'].strip()
   content=report['speech_analysis'];assert content['status']=='completed'
   assert (content['assessment']['level'] in ['alert','attention'])==risk,content
   item=dict(path=relative,report_id=key if keep else None,transcript=report['transcript'],speech_analysis=content,modules=report['modules'],passed=True)
   if kind=='video':
    before=copy.deepcopy(report['modules']);edited=requests.post(BASE+'/api/cases/'+key+'/speech-text',data={'text':'妈妈，今天晚上一起吃饭，明天去公园散步。'},timeout=180);edited.raise_for_status();value=edited.json();assert value['modules']==before;assert value['transcript']['corrected'];assert value['speech_analysis']['input_basis']=='user_corrected_transcript';item['correction_preserves_modules']=True
   out.append(item);(ROOT/'reports/speech-dual-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(relative,'PASS',content['assessment']['title'],flush=True)
  finally:
   if not keep:requests.delete(BASE+'/api/cases/'+key,timeout=15).raise_for_status()
 print('Actual audio/video, ASR, content and correction checks passed',flush=True)
if __name__=='__main__':main()
