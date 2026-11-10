"""Frozen temporal detector ensemble. Visual score only, never a fraud probability."""
import json,hashlib
from pathlib import Path
import torch
from transformers import VideoMAEImageProcessor,VideoMAEForVideoClassification
from bootstrap import ROOT
from .sifta import load_handler,score as xclip_score
from .media import sample_video
from .faces import face_views
from .video_math import fusion

class Bundle:
 def __init__(self,config):
  self.config=config;self.device='cuda' if torch.cuda.is_available() else 'cpu';self.xclip=load_handler();folder=ROOT/'models/video'
  if config.get('base_video_sha256') and hashlib.sha256((folder/'model.safetensors').read_bytes()).hexdigest()!=config['base_video_sha256']:raise RuntimeError('视频基础编码器版本校验失败')
  self.processor=VideoMAEImageProcessor.from_pretrained(folder,local_files_only=True);self.video=VideoMAEForVideoClassification.from_pretrained(folder,local_files_only=True).to(self.device).eval();path=ROOT/config['head']
  if hashlib.sha256(path.read_bytes()).hexdigest()!=config['head_sha256']:raise RuntimeError('视频分类头校验失败')
  self.video.classifier.load_state_dict(torch.load(path,map_location=self.device,weights_only=True));self.fake=next(int(k) for k,v in self.video.config.id2label.items() if v.lower()=='fake')
 def predict(self,path):
  first=xclip_score(self.xclip,path);_,frames=sample_video(path,16);images=[im for _,im in frames]
  while len(images)<16:images.append(images[-1])
  images,detected=face_views(images)
  with torch.inference_mode():second=self.video(**self.processor(images,return_tensors='pt').to(self.device)).logits.softmax(-1)[0,self.fake].item()
  value=fusion(first['score'],second,self.config['coefficients'])
  return dict(score=value,threshold=self.config.get('threshold',.5),moments=first['moments'],detector_scores={'X-CLIP':first['score'],'VideoMAE分类头':second},face_frames=detected)

def configured():
 p=ROOT/'models/active-video.json'
 if not p.exists():return False
 try:return json.loads(p.read_text()).get('engine')=='video-fusion'
 except (ValueError,OSError):return False

def predict(path):
 from .detector import lock
 info=json.loads((ROOT/'models/active-video.json').read_text())
 if info.get('approved') is not True:raise RuntimeError('视频版本尚未通过当前发布检查')
 with lock:
  bundle=Bundle(info)
  try:result=bundle.predict(path)
  finally:
   del bundle
   if torch.cuda.is_available():torch.cuda.empty_cache()
 return dict(result,status='completed',source=dict(repo='亲安双时序人脸核验 / X-CLIP + VideoMAE',version=info['version']),note='两套冻结时序编码器交叉核验人脸操纵，校准层只使用校准来源组。融合分数不是真实性或诈骗概率；不确认人物身份，不覆盖所有生成视频。')
