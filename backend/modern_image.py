"""Local isolated image inference, keeping website audio/video dependencies unchanged."""
import json,os,sys,subprocess,tempfile,math
from pathlib import Path
from bootstrap import ROOT
def configured():
 p=ROOT/'models/active-image.json'
 return p.exists() and json.loads(p.read_text(encoding='utf-8')).get('engine')=='smaug'
def available():
 return all((ROOT/p).exists() for p in ['models/smaug/model.safetensors','models/smaug/3_Dense/model.safetensors','runtime/smaug-packages/transformers','runtime/smaug-packages/sentence_transformers','runtime/smaug-packages/httpx2'])
def predict(image):
 from .detector import lock
 info=json.loads((ROOT/'models/active-image.json').read_text(encoding='utf-8'))
 if not info.get('approved') or not available():raise RuntimeError('Image release unavailable')
 with lock,tempfile.TemporaryDirectory(dir=ROOT/'runtime/tmp') as folder:
  path=Path(folder)/'input.png';image.save(path)
  env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONUTF8='1')
  result=subprocess.run([sys.executable,str(ROOT/'backend/smaug_worker.py'),str(path)],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8',timeout=180)
  if result.returncode:
   import logging
   logging.error('Image worker failed: %s',result.stderr[-5000:])
   raise RuntimeError('图片模型未能完成检查，请稍后重试。')
  output=json.loads(result.stdout.strip().splitlines()[-1]);value=output['score']
  if not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=1:raise RuntimeError('Invalid image score')
 return dict(status='completed',score=value,threshold=info['threshold'],sensitivity_threshold=info.get('sensitivity_threshold'),views=output.get('views',[]),sampling=output.get('sampling'),aggregation=output.get('aggregation'),source=dict(repo='abacusai/Smaug-AI-Image-Detector',version=info['version']),note='从同一张图片裁3个图块，分别检查AI生成特征后汇总。图块可重叠，框不是伪造位置，分数不是真假概率。不是通用修图检测器。')
