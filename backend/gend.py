"""Audited GenD CLIP architecture, initialized locally, strictly loaded from safetensors."""
import json,hashlib
import torch
from torch import nn
from torch.nn import functional as F
from transformers import CLIPModel,CLIPConfig,CLIPImageProcessor
from safetensors.torch import load_file
from bootstrap import ROOT
class Encoder(nn.Module):
 def __init__(self):
  super().__init__();clip=CLIPModel(CLIPConfig.from_json_file(str(ROOT/'vendor/gend/clip-config.json')));self.vision_model=clip.vision_model;self.visual_projection=clip.visual_projection
 def forward(self,x):return self.vision_model(x).pooler_output
class Probe(nn.Module):
 def __init__(self):super().__init__();self.linear=nn.Linear(1024,2)
 def forward(self,x):return self.linear(F.normalize(x,p=2,dim=1))
class GenD(nn.Module):
 def __init__(self):super().__init__();self.feature_extractor=Encoder();self.model=Probe()
 def forward(self,x):return self.model(self.feature_extractor(x))
def load():
 folder=ROOT/'models/gend-clip';source=json.loads((folder/'source.json').read_text());path=folder/'model.safetensors'
 if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:raise RuntimeError('GenD weight hash mismatch')
 with torch.device('meta'):model=GenD()
 model.load_state_dict(load_file(str(path)),strict=True,assign=True)
 # CLIP position_ids is a nonpersistent buffer, absent from the checkpoint.
 for module in model.modules():
  if hasattr(module,'position_ids') and module.position_ids.device.type=='meta':module.position_ids=torch.arange(module.position_ids.shape[-1]).expand((1,-1))
 if any(p.device.type=='meta' for p in model.parameters()):raise RuntimeError('Unloaded GenD parameter')
 device='cuda' if torch.cuda.is_available() else 'cpu';processor=CLIPImageProcessor(**json.loads((ROOT/'vendor/gend/clip-preprocessor_config.json').read_text()))
 return model.to(device=device,dtype=torch.float32).eval(),processor,device

def score(model,processor,device,path,details=False):
 from .media import sample_video
 from .faces import face_views
 _,frames=sample_video(path,8);images,_=face_views([im for _,im in frames],margin=1.3);out=[]
 for i in range(0,len(images),2):
  x=processor(images=images[i:i+2],return_tensors='pt')['pixel_values'].to(device)
  with torch.inference_mode():out.extend(model(x).softmax(-1)[:,1].cpu().tolist())
 value=sum(out)/len(out)
 return (value,[dict(start=float(t),score=float(s),threshold=.5) for (t,_),s in zip(frames,out)]) if details else value

def configured():
 p=ROOT/'models/active-video.json'
 return p.exists() and json.loads(p.read_text(encoding='utf-8')).get('engine')=='gend-clip'

def predict(path):
 from .detector import lock
 info=json.loads((ROOT/'models/active-video.json').read_text(encoding='utf-8'))
 if info.get('approved') is not True:raise RuntimeError('Video release is not approved')
 with lock:
  model,processor,device=load()
  try:value,moments=score(model,processor,device,path,details=True)
  finally:
   del model
   if torch.cuda.is_available():torch.cuda.empty_cache()
 return dict(status='completed',score=value,moments=moments,threshold=info['threshold'],source=dict(repo='yermandy/GenD_CLIP_L_14',version=info['version']),note='固定8帧、人脸优先裁剪1.3倍，个别未检出帧回退整帧；帧分数取均值。这是抽帧分类，不是连续时序或口型同步检测，不覆盖所有生成视频。')
