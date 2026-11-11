"""Read-only API verification of three public/fictional browser-uploaded fixtures."""
import bootstrap,json,requests
from bootstrap import ROOT

def main():
 base='http://127.0.0.1:8010'
 names=['fictional-chat.png','c36b704baf2bbb1121516c5cd03c9250a55df2e53c90b433be61bec524bd4add.wav','8f19947fe624345239215fe9dea8bff45f579028d7508f0bffcce87dcf808f19.wav']
 rows=requests.get(base+'/api/cases',timeout=10).json();out=[]
 for name in names:
  row=next(x for x in rows if x['filename']==name);r=requests.get(base+'/api/cases/'+row['id'],timeout=10).json()
  if name.endswith('.wav'):
   m=r['modules']['audio'];assert m['analysis_basis']=='acoustic_waveform_only'
   assert r['transcript']['status']=='disabled' and not r['phrases']
   positive=any(s['score']>=s['threshold'] for s in m['segments']);assert positive==name.startswith('8f199')
   out.append(dict(fixture=name,analysis_basis=m['analysis_basis'],positive=positive,segments=m['segments'],transcript_disabled=True,phrases_empty=True))
  else:
   assert r['scene']=='chat' and not r['modules']
   assert {s['category'] for s in r['chat_analysis']['signals']}=={'money','secrecy'}
   out.append(dict(fixture=name,scene='chat',no_acoustic_module=True,signals=r['chat_analysis']['signals']))
 (ROOT/'reports/voice-browser-acceptance.json').write_text(json.dumps(dict(actual_browser_uploads=True,api_checked=True,checks=out,scope='Functional regression of public / fictional fixtures, not another accuracy benchmark'),ensure_ascii=False,indent=2),encoding='utf-8')
 print('Three actual browser uploads verified against saved API reports')
if __name__=='__main__':main()
