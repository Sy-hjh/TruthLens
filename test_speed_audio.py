import bootstrap,unittest,tempfile,time,subprocess
from pathlib import Path
from unittest.mock import patch
import numpy as np,soundfile as sf,imageio_ffmpeg
from PIL import Image
from fastapi.testclient import TestClient
from backend.detector import audio_samples,AudioInputError
from backend import storage
from backend.app import app
class AudioSpeedChecks(unittest.TestCase):
 def test_stereo_phase_cancellation_keeps_audible_channel(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'phase.wav';x=.1*np.sin(2*np.pi*440*np.arange(32000)/16000);sf.write(p,np.stack([x,-x],1),16000)
   result=audio_samples(p,Path(d));self.assertGreater(float(np.sqrt(np.mean(result**2))),.02)
 def test_silence_and_short_have_distinct_causes(self):
  with tempfile.TemporaryDirectory() as d:
   for name,x,code in [('silent',np.zeros(32000),'silent'),('short',np.ones(8000)*.1,'too_short')]:
    p=Path(d)/(name+'.wav');sf.write(p,x,16000)
    with self.assertRaises(AudioInputError) as error:audio_samples(p,Path(d))
    self.assertEqual(error.exception.code,code)
 def test_video_without_audio_is_not_model_error(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'mute.mp4';subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-f','lavfi','-i','color=size=64x64:rate=25','-t','1.2','-an','-c:v','libx264',str(p)],check=True)
   with self.assertRaises(AudioInputError) as error:audio_samples(p,Path(d))
   self.assertEqual(error.exception.code,'no_audio_stream')
 def test_mp4_silent_first_track_uses_audible_second_track(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'tracks.mp4';subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-v','error','-f','lavfi','-i','color=size=64x64:rate=25','-f','lavfi','-i','anullsrc=r=16000:cl=stereo','-f','lavfi','-i','sine=frequency=500:sample_rate=16000','-map','0:v:0','-map','1:a:0','-map','2:a:0','-t','1.5','-c:v','libx264','-c:a','aac',str(p)],check=True)
   x=audio_samples(p,Path(d));self.assertGreater(float(np.sqrt(np.mean(x*x))),.01)
 def test_cached_cpu_asr_retains_source_metadata(self):
  from backend.mandarin import recognize
  from types import SimpleNamespace
  stream=SimpleNamespace(accept_waveform=lambda *a:None,result=SimpleNamespace(text='你好'))
  recognizer=SimpleNamespace(create_stream=lambda:stream,decode_stream=lambda s:None)
  with patch('backend.mandarin._recognizer',return_value=recognizer):value=recognize(np.ones(16000,dtype='float32'))
  self.assertEqual(value['text'],'你好');self.assertEqual(value['status'],'completed');self.assertIn('source',value)
 def test_voice_model_timeout_preserves_video_and_transcript(self):
  with tempfile.TemporaryDirectory() as d,patch.object(storage,'ROOT',Path(d)),patch('backend.app.sample_video',return_value=(2,[(0.,Image.new('RGB',(64,64)))])),patch('backend.ordered_video.configured',return_value=True),patch('backend.ordered_video.predict',return_value={'status':'completed','score':.1}),patch('backend.detector.audio_samples',return_value=np.ones(32000,dtype='float32')*.1),patch('backend.modern_voice.configured',return_value=True),patch('backend.modern_voice.predict',side_effect=TimeoutError('声音模型超时，不是无音轨')),patch('backend.detector.transcribe',return_value={'status':'completed','text':'今天一起吃饭'}),patch('backend.speech_content.analyze_text',return_value={'status':'completed','assessment':{'level':'uncertain'}}):
   client=TestClient(app);r=client.post('/api/analyze',files={'file':('test.mp4',b'public-test')});key=r.json()['job_id']
   deadline=time.monotonic()+30
   while time.monotonic()<deadline:
    job=client.get('/api/jobs/'+key).json()
    if job['status']!='processing':break
    time.sleep(.02)
   self.assertEqual(job['status'],'completed');value=job['result'];self.assertEqual(value['audio_info']['status'],'available');self.assertEqual(value['modules']['audio']['failure_stage'],'model');self.assertEqual(value['modules']['video']['status'],'completed');self.assertEqual(value['transcript']['text'],'今天一起吃饭');self.assertEqual(value['speech_analysis']['status'],'completed')
if __name__=='__main__':unittest.main()
