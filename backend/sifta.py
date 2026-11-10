"""Audited author-equivalent SIFTA face-clip inference, local files only."""
import json,hashlib
from bootstrap import ROOT

def configured():
 p=ROOT/'models/active-video.json'
 if not p.exists():return False
 try:return json.loads(p.read_text(encoding='utf-8')).get('engine')=='sifta'
 except ValueError:return False

def available():
 if not configured():return False
 try:
  info=json.loads((ROOT/'models/active-video.json').read_text());return info.get('approved') is True and (ROOT/'models/sifta/model.safetensors').exists()
 except (ValueError,OSError):return False

def load_handler():
 from vendor.sifta.handler import EndpointHandler
 folder=ROOT/'models/sifta';source=json.loads((folder/'source.json').read_text())
 if hashlib.sha256((folder/'model.safetensors').read_bytes()).hexdigest()!=source['sha256']:raise RuntimeError('视频权重校验失败')
 return EndpointHandler(str(folder))

def score(handler,path):
 import torch,numpy as np
 clips,total=handler._read_clips(str(path));per_face={};moments=[]
 for ci,(start,frames) in enumerate(clips):
  for fi,box in enumerate(handler._tracks(frames)):
   crops=[handler._crop(fr,box) for fr in frames];x=handler._tensor(crops).unsqueeze(0).to(handler.device)
   with torch.inference_mode():p=torch.softmax(handler.model(x).float()/handler.T,-1)[0,1].item()
   per_face.setdefault(fi,[]).append(p)
   if fi==0:moments.append(dict(start=start/handler._fps if handler._fps>0 else 0,score=p))
 if 0 not in per_face:raise ValueError('没有检出可用人脸，当前人脸操纵模型无法判断；声音仍可单独检查。')
 return dict(score=float(np.mean(per_face[0])),threshold=handler.threshold,moments=moments,clips_scored=len(per_face[0]),frames_read=total)

def predict(path):
 import torch
 from .detector import lock
 if not available():raise RuntimeError('已选择的视频模型尚未就绪，未切换成其他模型给分')
 info=json.loads((ROOT/'models/active-video.json').read_text())
 with lock:
  handler=load_handler();output=score(handler,path);del handler
  if torch.cuda.is_available():torch.cuda.empty_cache()
 return dict(output,status='completed',source=dict(repo='zodumair/sifta-deepfake-detector',version=info['version']),note='X-CLIP人脸操纵核验：4个短片段、每段8帧，对最大人脸分析；使用作者验证集温度与阈值，原始分数不是诈骗概率。不确认人物身份，不覆盖所有整段生成视频。')
