import bootstrap,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from fastapi.testclient import TestClient
from backend.speech_content import check
from backend.app import app
from backend import storage
class SpeechTests(unittest.TestCase):
 def test_text_branch_receives_transcript_only(self):
  samples=np.ones(16000,dtype='float32');t=dict(status='completed',text='先借我两千，不要给我打电话。')
  with patch('backend.detector.transcribe',return_value=t) as asr,patch('backend.speech_content.analyze_text',return_value={'status':'completed'}) as text:
   self.assertEqual(check(samples)[0],t);self.assertIs(asr.call_args.args[0],samples);text.assert_called_once_with(t['text'])
 def test_empty_asr_never_fabricates_content(self):
  with patch('backend.detector.transcribe',return_value=dict(status='completed',text='')),patch('backend.speech_content.analyze_text') as text:
   self.assertEqual(check(np.ones(16000))[1]['status'],'unavailable');text.assert_not_called()
 def test_asr_failure_is_explicit(self):
  with patch('backend.detector.transcribe',side_effect=RuntimeError('ASR unavailable')):
   t,c=check(np.ones(16000));self.assertEqual(t['status'],'unavailable');self.assertEqual(c['status'],'unavailable')
 def test_content_failure_keeps_transcript(self):
  with patch('backend.detector.transcribe',return_value=dict(status='completed',text='原始文字')),patch('backend.speech_content.analyze_text',side_effect=RuntimeError('unavailable')):
   t,c=check(np.ones(16000));self.assertEqual(t['text'],'原始文字');self.assertEqual(c['status'],'unavailable')
 def test_credential_mention_without_request_rejected(self):
  import json
  from backend.chat_analysis import validate
  text='奶奶你好我们一起去公园不涉及转账和验证码'
  self.assertEqual(validate(json.dumps({'signals':[{'category':'credentials','quote':text}]},ensure_ascii=False),text),[])
  for text in ['把刚收到的六位数字念给我','验证码发给我']:
   self.assertEqual(len(validate(json.dumps({'signals':[{'category':'credentials','quote':text}]},ensure_ascii=False),text)),1)
 def test_correction_does_not_rewrite_audio_or_video(self):
  with tempfile.TemporaryDirectory() as directory,patch.object(storage,'ROOT',Path(directory)):
   modules={'audio':{'score':.08,'status':'completed'},'video':{'score':.9,'status':'completed'}}
   storage.save(dict(id='speech-edit',scene='general',modules=modules,transcript={'text':'原转写'}))
   with patch('backend.speech_content.analyze_text',return_value={'status':'completed','assessment':{'level':'alert'}}):
    response=TestClient(app).post('/api/cases/speech-edit/speech-text',data={'text':'借我两千，不要打电话'})
   self.assertEqual(response.status_code,200);r=response.json();self.assertEqual(r['modules'],modules);self.assertEqual(r['transcript']['original_text'],'原转写');self.assertTrue(r['transcript']['corrected']);self.assertEqual(r['speech_analysis']['input_basis'],'user_corrected_transcript')
   with patch('backend.speech_content.analyze_text',return_value={'status':'completed','assessment':{'level':'uncertain'}}):
    r=TestClient(app).post('/api/cases/speech-edit/speech-text',data={'text':'今天一起吃饭'}).json()
   self.assertEqual(r['modules'],modules);self.assertEqual(r['summary'],'发现合成线索，请先核实');self.assertEqual(r['transcript']['original_text'],'原转写')
if __name__=='__main__':unittest.main()
