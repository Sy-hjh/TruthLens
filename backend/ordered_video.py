"""Locally trained ordered head; public-feature caches are NEVER used for uploads."""
import json,hashlib,gc
import torch
import numpy as np
from PIL import Image
from torch.nn import functional as F
from bootstrap import ROOT

def configured():
 path=ROOT/'models/active-video.json'
 return path.exists() and json.loads(path.read_text(encoding='utf-8')).get('engine')=='video-ordered-head'

def predict(path):
 from .detector import lock
 from .gend import load
 from fakestormer_candidate import read_clips
 from train_temporal_sequence import OrderedHead
 config=json.loads((ROOT/'models/active-video.json').read_text(encoding='utf-8'))
 if config.get('approved') is not True:raise RuntimeError('Ordered video release not approved')
 protocol=json.loads((ROOT/config['protocol']).read_text(encoding='utf-8'))
 for name,expected in [('train_temporal_sequence.py',protocol['code_sha']),('fakestormer_candidate.py',protocol['sampler_sha']), (config['head'],protocol['checkpoint_sha'])]:
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('Ordered inference integrity mismatch: '+name)
 source=json.loads((ROOT/'models/gend-clip/source.json').read_text())
 if source['sha256']!=protocol['encoder_sha']:raise RuntimeError('Ordered encoder mismatch')
 with lock:
  encoder=processor=head=None
  try:
   encoder,processor,device=load();head=OrderedHead().to(device);head.load_state_dict(torch.load(ROOT/config['head'],weights_only=True,map_location=device)['head']);head.eval();traces=[];features=[];base=[]
   for trace,x in read_clips(path):
    rgb=(x*torch.tensor([.229,.224,.225])[:,None,None,None]+torch.tensor([.485,.456,.406])[:,None,None,None]).permute(1,2,3,0).clamp(0,1);images=[Image.fromarray((frame.numpy()*255).round().astype('uint8')) for frame in rgb];inputs=processor(images=images,return_tensors='pt')['pixel_values'].to(device)
    with torch.inference_mode():
     value=F.normalize(encoder.feature_extractor(inputs),dim=1);raw=encoder.model.linear(value);features.append(value.half().float());base.append((raw[:,1]-raw[:,0]).mean())
    traces.append(trace)
   values=torch.stack(features)[None];raw=torch.stack(base)[None];mask=torch.ones_like(raw)
   with torch.inference_mode():
    score=float(head(values,raw,mask).sigmoid()[0]);moments=[]
    for i,trace in enumerate(traces):
     value=float(head(values[:,i:i+1],raw[:,i:i+1],mask[:,i:i+1]).sigmoid()[0]);moments.append(dict(start=trace['start'],end=trace['end'],score=value,frame_indices=trace['frame_indices'],input_frames=4))
  finally:
   del encoder,processor,head;gc.collect()
   if torch.cuda.is_available():torch.cuda.empty_cache()
 return dict(status='completed',score=score,threshold=config['threshold'],method='temporal-sequence',moments=moments,source=dict(repo='QinAn/frozen-GenD-ordered-GRU',version=config['version']),note='冻结图像编码器，本地训练双向GRU；每段32帧范围内的4个有序画面共同分析，最多4段。并非32帧全输入；不检测口型同步，不覆盖所有生成视频。曲线为片段输出，提醒线为整视频验证阈值，未单独校准片段。')
