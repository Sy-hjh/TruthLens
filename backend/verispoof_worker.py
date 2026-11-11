"""One local waveform job, isolated dependencies; never transcribes or reads user text."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import bootstrap,numpy as np
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
if __name__=='__main__':
 try:main()
 except Exception:
  import traceback
  (ROOT/'runtime/verispoof-worker-error.log').write_text(traceback.format_exc(),encoding='utf-8')
  raise
