"""One local waveform job, isolated dependencies; never transcribes or reads user text."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import bootstrap,numpy as np
import torch,gc,time
torch.set_num_threads(2)
torch.set_num_interop_threads(1)
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(8*1024*1024):h.update(chunk)
 return h.hexdigest()
def main():
 source=json.loads((ROOT/'models/verispoof/source.json').read_text())
 for file,expected in source['sha256'].items():
  if digest(ROOT/'models/verispoof'/file)!=expected:raise RuntimeError('Acoustic model hash mismatch')
 from verispoof_local import load
 from backend.acoustic_protocol import analyze
 x=np.load(sys.argv[1],allow_pickle=False)
 if x.ndim!=1 or len(x)>2880000 or not np.isfinite(x).all():raise ValueError('Invalid waveform')
 model=load();parts=analyze(model,x)
 print(json.dumps({'segments':parts}),flush=True)
def move(model,device):
 model.net.to(device)
 # AudioEncoder is intentionally a plain class, not an nn.Module child.
 model.net.encoder.encoder.to(device);model.net.encoder.logmel.to(device)
 model.net.encoder.device=device

def serve():
 source=json.loads((ROOT/'models/verispoof/source.json').read_text())
 for file,expected in source['sha256'].items():
  if digest(ROOT/'models/verispoof'/file)!=expected:raise RuntimeError('Acoustic model hash mismatch')
 from verispoof_local import load
 from backend.acoustic_protocol import analyze
 model=load();move(model,'cpu');gc.collect();torch.cuda.empty_cache()
 print(json.dumps({'ready':True}),flush=True)
 for line in sys.stdin:
  request=json.loads(line);started=time.monotonic()
  try:
   x=np.load(request['path'],allow_pickle=False)
   if x.ndim!=1 or len(x)>2880000 or not np.isfinite(x).all():raise ValueError('Invalid waveform')
   move(model,'cuda');parts=analyze(model,x)
   response={'id':request['id'],'segments':parts,'inference_seconds':time.monotonic()-started}
  except Exception as exc:
   import traceback
   traceback.print_exc(file=sys.stderr);response={'id':request['id'],'error':type(exc).__name__+': '+str(exc)[:200]}
  finally:
   move(model,'cpu');model.net.encoder._hs=[];gc.collect();torch.cuda.empty_cache()
  print(json.dumps(response),flush=True)
  # Retain only model weights between jobs, not the previous waveform or reply.
  x=None;parts=None;request=None;response=None;line=None
if __name__=='__main__':
 try:
  if len(sys.argv)>1 and sys.argv[1]=='--serve':serve()
  else:main()
 except Exception:
  import traceback
  (ROOT/'runtime/verispoof-worker-error.log').write_text(traceback.format_exc(),encoding='utf-8')
  raise
