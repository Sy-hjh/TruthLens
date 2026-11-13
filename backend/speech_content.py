"""Independent waveform-to-text risk check; never changes synthesis scores."""
def analyze_text(text):
 from .chat_analysis import analyze
 value=analyze(text[:4000]);value['input_basis']='speech_transcript';return value

def check(samples,transcript=None):
 from .detector import transcribe
 try:
  if transcript is None:transcript=transcribe(samples)
  if transcript.get('status')!='completed' or not transcript.get('text','').strip():return transcript,dict(status='unavailable',signals=[],note='没有取得可分析的转写文字，不能判断内容风险。')
 except Exception:
  import logging
  logging.exception('Speech transcription failed independently')
  return dict(status='unavailable',text='',note='声音转文字未完成，声学检查结果单独保留。'),dict(status='unavailable',signals=[],note='转写不可用，未完成内容分析。')
 try:content=analyze_text(transcript['text'])
 except Exception:
  import logging
  logging.exception('Speech content analysis failed independently')
  content=dict(status='unavailable',signals=[],note='已有转写，内容分析暂不可用；请核对文字。')
 return transcript,content
