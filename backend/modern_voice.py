"""Isolated acoustic-only VeriSpoof deployment. No text, ASR or filename sent to model."""
import json,subprocess,sys,os,tempfile,logging
import numpy as np
from pathlib import Path
from bootstrap import ROOT
def configured():
 p=ROOT/'models/active-audio.json'
 return p.exists() and json.loads(p.read_text()).get('engine')=='verispoof'
def available():
 try:
  import torch
  if not torch.cuda.is_available():return False
  info=json.loads((ROOT/'models/active-audio.json').read_text())
  if not info.get('approved'):return False
  if info.get('secondary') and not (ROOT/info['secondary']['weights']).is_file():return False
  source=json.loads((ROOT/'models/verispoof/source.json').read_text())
  return (ROOT/'runtime/smaug-packages/transformers').exists() and all((ROOT/'models/verispoof'/p).is_file() for p in source['sha256'])
 except (OSError,ValueError,KeyError):return False
def predict(samples):
 from .detector import lock
 info=json.loads((ROOT/'models/active-audio.json').read_text())
 if not info.get('approved') or not available():raise RuntimeError('声音检测模型未就绪')
 with lock,tempfile.TemporaryDirectory(dir=ROOT/'runtime/tmp') as directory:
  path=Path(directory)/'waveform.npy';np.save(path,np.asarray(samples,dtype=np.float32),allow_pickle=False)
  env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONUTF8='1')
  result=subprocess.run([sys.executable,str(ROOT/'backend/verispoof_worker.py'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=300)
  if result.returncode:
   logging.error('Acoustic worker failed: %s',result.stderr[-5000:]);raise RuntimeError('声音检测未完成；请查看运行日志或换一段清晰录音重试。')
  parts=json.loads(result.stdout.strip().splitlines()[-1])['segments']
 source=dict(repo='AustinXiao/VeriSpoof-Plus',version=info['version'])
 for part in parts:part['source']=source
 secondary=None
 # The primary process has exited and released its GPU memory and lock.
 # Decisions use each model's own threshold; scores are not averaged.
 if info.get('secondary') and not any(p['score']>=p['threshold'] for p in parts):
  from .voice_forensics import predict as secondary_predict
  secondary=secondary_predict(samples,release=info['secondary'])
  if secondary['score']>=secondary['threshold']:
   start=max(0,(len(samples)/16000-5)/2)
   parts.append(dict(secondary,start=start,end=min(len(samples)/16000,start+5),check='secondary'))
 return dict(status='completed',segments=parts,source=source,secondary_check=secondary,analysis_basis='acoustic_waveform_only',sample_rate=16000,analyzed_seconds=len(samples)/16000,note='直接分析声音波形，不进行语音转写或话术匹配。主模型每8秒检查、重叠4秒；未检出时用独立声学模型复查录音中间5秒。短录音重复补齐输入，实际时长不变。')
