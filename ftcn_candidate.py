"""Isolated historical FTCN+TT baseline. 32 consecutive frames, real temporal network.
Not activated automatically. YuNet fixed-box preprocessing differs from author alignment.
Only run this standalone: its compatibility module names must not enter the web process.
"""
import bootstrap,sys,types,logging,json,hashlib,importlib.util
from pathlib import Path
import numpy as np,torch,cv2
ROOT=bootstrap.ROOT;SOURCE=ROOT/'runtime/ftcn-source'
def package(name,path):
 m=types.ModuleType(name);m.__path__=[str(path)];sys.modules[name]=m
def load():
 sys.path.insert(0,str(ROOT/'runtime/ftcn-packages'))
 for name in ['slowfast','slowfast.models','slowfast.config','slowfast.utils','model','model.classifier']:
  package(name,SOURCE/Path(*name.split('.')))
 class Values(types.SimpleNamespace):
  def to_dict(self):return self.__dict__.copy()
 cfg=Values(clip_size=32,model=Values(inco=Values(no_time_pool=False,spatial_count=0,keep_stride_count=0,i3d_routine=True,SOLVER=None),transformer=Values(patch_type='time',dim=-1,stop_point=5,depth=1,random_select=True,k=8)))
 config=types.ModuleType('config');config.config=cfg;sys.modules['config']=config
 utils=types.ModuleType('utils');utils.logger=logging.getLogger('ftcn');sys.modules['utils']=utils
 name='model.classifier.i3d_temporal_var_fix_dropout_tt_cfg';module=types.ModuleType(name);module.__package__='model.classifier';sys.modules[name]=module
 source=(SOURCE/'model/classifier/i3d_temporal_var_fix_dropout_tt_cfg.py').read_text(encoding='utf-8');source=source[:source.index('\nfrom torch import nn\nfrom typing import Callable')]
 # Modern torch added constructor-only device/dtype; these are not Conv3d attributes.
 source=source.replace('parameters = [parameter for parameter in signature(nn.Conv3d).parameters]','parameters = [parameter for parameter in signature(nn.Conv3d).parameters if parameter not in ("device", "dtype")]')
 exec(compile(source,str(SOURCE/'model/classifier/i3d_temporal_var_fix_dropout_tt_cfg.py'),'exec'),module.__dict__)
 model=module.I3D8x8()
 folder=ROOT/'models/ftcn';meta=json.loads((folder/'source.json').read_text());path=folder/'author-weights.pth'
 assert hashlib.sha256(path.read_bytes()).hexdigest()==meta['sha256']
 state=torch.load(path,map_location='cpu',weights_only=True)
 print('checkpoint keys',list(state)[:10],flush=True)
 if 'state_dict' in state:state=state['state_dict']
 if 'model' in state and isinstance(state['model'],dict):state=state['model']
 # Strip only known wrapper prefixes; strict loading rejects every unmatched tensor.
 for prefix in ['module.','net.','model.']:
  if all(k.startswith(prefix) for k in state):state={k[len(prefix):]:v for k,v in state.items()}
 model.load_state_dict(state,strict=True)
 return model.to('cuda' if torch.cuda.is_available() else 'cpu').eval()

def clips(path,limit=4):
 cap=cv2.VideoCapture(str(path));fps=cap.get(cv2.CAP_PROP_FPS);count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
 if fps<=0 or count<32:cap.release();raise ValueError('至少需要32个连续帧，不能用重复帧冒充时序。')
 if count/fps>180:cap.release();raise ValueError('最长支持180秒。')
 detector=cv2.FaceDetectorYN.create(str(ROOT/'models/face-detector/model.onnx'),'',(320,320),.8,.3,5000);output=[]
 try:
  for start in sorted(set(round(x) for x in np.linspace(0,count-32,min(limit,max(1,count//32))))):
   cap.set(cv2.CAP_PROP_POS_FRAMES,start);frames=[];boxes=[];last=None
   for j in range(32):
    ok,bgr=cap.read()
    if not ok:break
    h,w=bgr.shape[:2];scale=min(1.,640/max(h,w));small=cv2.resize(bgr,(round(w*scale),round(h*scale)));detector.setInputSize((small.shape[1],small.shape[0]));_,faces=detector.detect(small)
    if faces is None:break
    if last is None:face=max(faces,key=lambda f:f[2]*f[3])
    else:face=min(faces,key=lambda f:np.linalg.norm((f[:2]+f[2:4]/2)/scale-last))
    x,y,bw,bh=face[:4]/scale;center=np.array([x+bw/2,y+bh/2])
    if last is not None and np.linalg.norm(center-last)>max(bw,bh):break
    last=center;side=max(bw,bh)*1.4;boxes.append([center[0]-side/2,center[1]-side/2,center[0]+side/2,center[1]+side/2]);frames.append(bgr)
   if len(frames)!=32:continue
   # One box for a whole clip: detector jitter cannot create artificial frame flicker.
   box=np.asarray(boxes);x1,y1=np.floor(box[:,:2].min(0)).astype(int);x2,y2=np.ceil(box[:,2:].max(0)).astype(int);x1=max(0,x1);y1=max(0,y1);x2=min(w,x2);y2=min(h,y2)
   arrays=[cv2.cvtColor(cv2.resize(fr[y1:y2,x1:x2],(224,224)),cv2.COLOR_BGR2RGB) for fr in frames]
   x=torch.tensor(np.stack(arrays)).permute(3,0,1,2).float()/255;x=(x-torch.tensor([.485,.456,.406])[:,None,None,None])/torch.tensor([.229,.224,.225])[:,None,None,None]
   output.append((dict(start=start/fps,end=(start+31)/fps,frame_indices=list(range(start,start+32))),x))
 finally:cap.release()
 if not output:raise ValueError('没有连续32帧可跟踪人脸，时序模型无法判断。')
 return output

def predict(model,path):
 values=[];device=next(model.parameters()).device
 for trace,x in clips(path):
  with torch.inference_mode():score=float(model(x.unsqueeze(0).to(device))['final_output'].view(-1)[0])
  values.append(dict(trace,score=score))
 return dict(score=float(np.mean([v['score'] for v in values])),clips=values)
if __name__=='__main__':
 torch.set_num_threads(2);m=load();print(predict(m,ROOT/'data/demo/known-fake.mp4'),flush=True)
