"""Ensure fraud-like words cannot drive the acoustic synthesis result."""
import bootstrap,unittest,tempfile,time
from pathlib import Path
from unittest.mock import patch
import numpy as np
from fastapi.testclient import TestClient
from backend import storage
from backend.app import app
from backend.chat_analysis import validate
class IsolationTests(unittest.TestCase):
 def test_cascade_keeps_independent_thresholds_and_skips_positive_primary(self):
  from backend.modern_voice import predict
  from types import SimpleNamespace
  info=dict(approved=True,version='test',secondary={'threshold':.7})
  for primary,secondary,expected_calls,expected_positive in ((.9,.8,0,True),(.1,.69,1,False),(.1,.71,1,True)):
   parts=[dict(start=0,end=4,score=primary,threshold=.5)]
   with patch('backend.modern_voice.available',return_value=True),patch('backend.modern_voice.json.loads',side_effect=[info,{'segments':parts}]),patch('backend.modern_voice.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='{}')),patch('backend.voice_forensics.predict',return_value=dict(status='completed',score=secondary,threshold=.7,source={})) as second:
    result=predict(np.ones(64000,dtype=np.float32))
    self.assertEqual(second.call_count,expected_calls)
    self.assertEqual(any(s['score']>=s['threshold'] for s in result['segments']),expected_positive)
    self.assertEqual(result['segments'][0]['score'],primary)
 def test_modern_acoustic_branch_never_uses_words(self):
  module=dict(status='completed',analysis_basis='acoustic_waveform_only',segments=[dict(start=0,end=4,score=.1,threshold=.5)])
  with tempfile.TemporaryDirectory() as tmp,patch.object(storage,'ROOT',Path(tmp)),patch('backend.detector.audio_samples',return_value=np.full(64000,.1,dtype=np.float32)),patch('backend.modern_voice.configured',return_value=True),patch('backend.modern_voice.predict',return_value=module) as acoustic,patch('backend.detector.transcribe',side_effect=AssertionError('No transcription')):
   client=TestClient(app);r=client.post('/api/analyze',files={'file':('妈妈马上转钱.wav',b'RIFF-test')},data={'context':'不要打电话，转到新账户'})
   key=r.json()['job_id']
   for _ in range(100):
    job=client.get('/api/jobs/'+key).json()
    if job['status']!='processing':break
    time.sleep(.02)
   self.assertEqual(job['status'],'completed');self.assertEqual(job['result']['phrases'],[]);self.assertEqual(job['result']['transcript']['status'],'disabled');self.assertEqual(job['result']['modules']['audio'],module)
   self.assertEqual(len(acoustic.call_args.args),1);self.assertIsInstance(acoustic.call_args.args[0],np.ndarray)
 def test_audio_never_calls_transcription_or_text_analysis(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(storage,'ROOT',Path(tmp)),patch('backend.detector.audio_samples',return_value=np.full(64000,.1,dtype=np.float32)),patch('backend.modern_voice.configured',return_value=False),patch('backend.detector.transcribe',side_effect=AssertionError('Must not transcribe')) as transcribe,patch('backend.detector.classify',return_value={'status':'completed','score':.1,'threshold':.5}):
   client=TestClient(app);r=client.post('/api/analyze',files={'file':('real.wav',b'RIFF-test')},data={'context':'妈妈急需用钱，给我转点呗'});self.assertEqual(r.status_code,202);key=r.json()['job_id']
   for _ in range(100):
    job=client.get('/api/jobs/'+key).json()
    if job['status']!='processing':break
    time.sleep(.02)
   self.assertEqual(job['status'],'completed');self.assertEqual(job['result']['phrases'],[]);self.assertEqual(job['result']['transcript']['status'],'disabled');self.assertEqual(job['result']['modules']['audio']['segments'][0]['score'],.1);transcribe.assert_not_called()
 def test_chat_mode_rejects_audio_before_processing(self):
  response=TestClient(app).post('/api/analyze',files={'file':('x.wav',b'x')},data={'scene':'chat'});self.assertEqual(response.status_code,422)
 def test_chat_evidence_must_match_actual_screenshot(self):
  with self.assertRaises(ValueError):validate('{"signals":[{"category":"money","quote":"转账到安全账户"}]}','明天一起吃饭')
 def test_chat_model_output_cannot_be_arbitrary_categories(self):
  with self.assertRaises(ValueError):validate('{"signals":[{"category":"definitely_fraud","quote":"先借我两千"}]}','先借我两千')
if __name__=='__main__':unittest.main()
