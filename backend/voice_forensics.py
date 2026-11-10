"""Local XLS-R/AASIST inference. No implicit downloads or pickle loading."""
import json,hashlib
from bootstrap import ROOT
_cached_model=None
_cached_signature=None

def available():
 p=ROOT/'models/active-audio.json'
 if not p.exists():return False
 try:
  info=json.loads(p.read_text(encoding='utf-8'));return info.get('approved') is True and (ROOT/info['weights']).is_file()
 except (ValueError,KeyError,OSError):return False

def configured():return (ROOT/'models/active-audio.json').exists()

def load_model():
 import torch
 from safetensors.torch import load_file
 from vendor.audio_forensics.model import DeepfakeDetector
 path=ROOT/'models/audio-forensics/checkpoint_epoch_4.safetensors';source=json.loads((path.parent/'source.json').read_text())
 if hashlib.sha256(path.read_bytes()).hexdigest()!=source['sha256']:raise RuntimeError('声音模型权重校验失败')
 model=DeepfakeDetector();state=load_file(str(path))
 # The author's published inference class does not reference these four tensors.
 # Unlike its broad strict=False example, allow only this explicit unused set;
 # all parameters actually used for inference must still load strictly.
 unused={'projection.0.bias','projection.0.weight','projection.2.bias','projection.2.weight'}
 extras=set(state)-set(model.state_dict())
 if extras!=unused:raise RuntimeError('声音权重与已审核推理架构不匹配')
 model.load_state_dict({k:v for k,v in state.items() if k not in unused},strict=True)
 return model.eval()

def waveform(samples):
 import torch
 x=torch.as_tensor(samples,dtype=torch.float32);x=x/(x.abs().max()+1e-8);n=80000
 if len(x)<n:x=x.repeat((n+len(x)-1)//len(x))[:n]
 elif len(x)>n:
  start=(len(x)-n)//2;x=x[start:start+n]
 return x.unsqueeze(0)

def predict(samples):
 global _cached_model,_cached_signature
 import torch
 from .detector import lock
 info=json.loads((ROOT/'models/active-audio.json').read_text(encoding='utf-8'))
 with lock:
  path=ROOT/info['weights'];stat=path.stat();signature=(info['weights_sha256'],stat.st_size,stat.st_mtime_ns)
  if _cached_model is None or signature!=_cached_signature:
   if hashlib.sha256(path.read_bytes()).hexdigest()!=info['weights_sha256']:raise RuntimeError('启用的声音模型版本校验失败')
   _cached_model=load_model();_cached_signature=signature
  device='cuda' if torch.cuda.is_available() else 'cpu';model=_cached_model.to(device)
  try:
   with torch.inference_mode():score=1-model(waveform(samples).to(device)).sigmoid().item()
  finally:
   model.cpu()
   if device=='cuda':torch.cuda.empty_cache()
 return dict(status='completed',score=score,threshold=info['threshold'],source=dict(repo='eliya/forensics_0.3B_xlsr_wild_deepfake_classifier',version=info['version']),note='XLS-R/AASIST声音合成线索；每段取中间5秒或重复补齐。原始模型分数不是诈骗概率，不能确认说话者身份。')
