"""Audited FakeSTormer classification path, without legacy MMCV training runtime.
All backbone and classification tensors strictly loaded. Auxiliary training-only
heatmap/temporal-localization heads do not feed classification and are omitted.
Four frames are processed jointly with spatial AND temporal attention.
"""
import bootstrap,ast,json,hashlib,types,gc
from pathlib import Path
import numpy as np,torch
import cv2
from torch import nn
ROOT=bootstrap.ROOT
def load():
 source=ROOT/'runtime/fakestormer-source/models/networks/backbones/vit.py';body=source.read_bytes()
 tree=json.loads((ROOT/'runtime/fakestormer-tree.json').read_text());entry=next(x for x in tree['tree'] if x['path']=='models/networks/backbones/vit.py')
 assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==entry['sha'],'Author code hash mismatch'
 nodes=[]
 for node in ast.parse(body).body:
  if isinstance(node,ast.ImportFrom) and (node.level>0 or node.module=='models.builder'):continue
  nodes.append(node)
 class Registry:
  def register_module(self):return lambda cls:cls
 namespace=dict(BACKBONES=Registry(),BaseBackbone=nn.Module,BN3D_MOMENTUM=.05)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),namespace)
 class Detector(nn.Module):
  def __init__(self):
   super().__init__();self.backbone=namespace['TimeViT'](img_size=[224,224],patch_size=16,embed_dim=768,depth=12,num_heads=12,mlp_ratio=4,qkv_bias=True,drop_path_rate=.3,class_token=True,register_token=False,temp_token=True,attention_type='divided_space_time',num_frames=4,low_level_enhanced=False)
   self.keypoint_head=nn.Module();self.keypoint_head.cls=nn.Module();self.keypoint_head.cls.fc_out=nn.Linear(768,1)
  def forward(self,x):
   features=self.backbone(x)['cls'];return self.keypoint_head.cls.fc_out(features.reshape(x.shape[0],-1)).view(-1)
 folder=ROOT/'models/fakestormer';meta=json.loads((folder/'source.json').read_text(encoding='utf-8'));path=folder/'author-c0.pth'
 assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['sha256'],'Author weights hash mismatch'
 state=torch.load(path,map_location='cpu',weights_only=True,mmap=True)
 print('Checkpoint fields',list(state)[:7],flush=True)
 for key in ['state_dict','model']:
  if key in state and isinstance(state[key],dict):state=state[key];break
 if all(k.startswith('module.') for k in state):state={k[7:]:v for k,v in state.items()}
 accepted={k:v for k,v in state.items() if k.startswith('backbone.') or k.startswith('keypoint_head.cls.')}
 unexpected=[k for k in state if k not in accepted and not k.startswith(('keypoint_head.hm.','keypoint_head.temp_loc.'))]
 if unexpected:raise RuntimeError('Unexpected inference tensors: '+str(unexpected[:10]))
 model=Detector();model.load_state_dict(accepted,strict=True,assign=True);del state,accepted;gc.collect()
 model=model.to('cuda' if torch.cuda.is_available() else 'cpu').eval();print('Strictly loaded trained temporal backbone and classification head',flush=True);return model

def read_clips(path,limit=4):
 """Decode ordered spans; detect only the four frames actually entering the model."""
 cv2.setNumThreads(1);cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS);count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));selected=[0,10,21,31];out=[]
 if fps<=0 or count<32 or count/fps>180:cap.release();raise ValueError('视频需包含32帧且不超过3分钟；不能重复帧冒充时序。')
 try:
  model=(ROOT/'models/face-detector/model.onnx').read_bytes()
  detector=cv2.FaceDetectorYN.create('onnx',model,b'',(320,320),.8,.3,5000)
  for start in sorted(set(round(v) for v in np.linspace(0,count-32,min(limit,max(1,count//32))))):
   cap.set(cv2.CAP_PROP_POS_FRAMES,start);frames=[];boxes=[];center=None
   for j in range(32):
    ok,frame=cap.read()
    if not ok:break
    if j not in selected:continue
    h,w=frame.shape[:2];scale=min(1.,640/max(h,w));small=cv2.resize(frame,(round(w*scale),round(h*scale)));detector.setInputSize((small.shape[1],small.shape[0]));_,faces=detector.detect(small)
    if faces is None:break
    face=max(faces,key=lambda f:f[2]*f[3]) if center is None else min(faces,key=lambda f:np.linalg.norm((f[:2]+f[2:4]/2)/scale-center));x,y,bw,bh=face[:4]/scale;newcenter=np.array([x+bw/2,y+bh/2])
    if center is not None and np.linalg.norm(newcenter-center)>max(bw,bh):break
    center=newcenter;side=max(bw,bh)*1.4;boxes.append([center[0]-side/2,center[1]-side/2,center[0]+side/2,center[1]+side/2]);frames.append(frame)
   if len(frames)!=4:continue
   bounds=np.asarray(boxes);x1,y1=np.floor(bounds[:,:2].min(0)).astype(int);x2,y2=np.ceil(bounds[:,2:].max(0)).astype(int);x1=max(0,x1);y1=max(0,y1);x2=min(w,x2);y2=min(h,y2)
   images=[cv2.cvtColor(cv2.resize(fr[y1:y2,x1:x2],(224,224)),cv2.COLOR_BGR2RGB) for fr in frames];x=torch.from_numpy(np.stack(images)).permute(3,0,1,2).float()/255;x=(x-torch.tensor([.485,.456,.406])[:,None,None,None])/torch.tensor([.229,.224,.225])[:,None,None,None]
   out.append((dict(start=start/fps,end=(start+31)/fps,frame_indices=[start+i for i in selected],input_frames=4),x))
 finally:cap.release()
 if not out:raise ValueError('没有取得可用的有序人脸片段，时序检查无法判断。')
 return out

def predict(model,path,limit=4,order='original'):
 out=[];device=next(model.parameters()).device
 for trace,x in read_clips(path,limit=limit):
  if order=='reverse':x=x.flip(1)
  elif order=='shuffle':x=x[:,torch.tensor([2,0,3,1])]
  elif order=='repeat':x=x[:,[0,0,0,0]]
  with torch.inference_mode():raw=float(model(x.unsqueeze(0).to(device))[0]);value=float(torch.sigmoid(torch.tensor(raw)))
  out.append(dict(trace,score=value,logit=raw))
 return dict(score=float(np.mean([r['score'] for r in out])),clips=out,method='4-frame joint divided-space-time attention per32consecutive-frame span; up to4spans; face-only, no lip-sync')
if __name__=='__main__':
 torch.set_num_threads(2);model=load();print(predict(model,ROOT/'data/demo/known-fake.mp4'),flush=True)
