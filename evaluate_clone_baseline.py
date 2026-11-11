"""Acoustic-only Mandarin clone diagnostic; labels never enter model inputs."""
import bootstrap,json,math
import torch,numpy as np,soundfile as sf
from scipy.signal import resample_poly
from backend.voice_forensics import load_model,waveform
from check_recent_model import statistics
def samples(path):
 x,sr=sf.read(path,dtype='float32',always_2d=True);x=x.mean(1)
 if sr!=16000:
  g=math.gcd(sr,16000);x=resample_poly(x,16000//g,sr//g)
 return x.astype(np.float32)
def main():
 root=bootstrap.ROOT;p=root/'data/clone-bench/manifest.json'
 if not p.exists():p=p.with_name('manifest.partial.json')
 rows=[r for r in json.loads(p.read_text(encoding='utf-8')) if r['split']=='val'];model=load_model().to('cuda' if torch.cuda.is_available() else 'cpu');device=next(model.parameters()).device
 results=[]
 for i in range(0,len(rows),4):
  batch=rows[i:i+4];x=torch.cat([waveform(samples(root/r['path'])) for r in batch]).to(device)
  with torch.inference_mode():scores=(1-model(x).sigmoid()).cpu().tolist()
  results.extend(dict(r,score=float(p),predicted=int(p>=.5)) for r,p in zip(batch,scores))
  if i%40==0:print('Clone validation diagnostic',i,'/',len(rows),flush=True)
 report=dict(scope='Validation-only diagnostic; center 5s author input; no speech transcription or text classifier used.',metrics=statistics(results),by_generator={g:statistics([r for r in results if r['generator'] in (g,'human')]) for g in sorted({r['generator'] for r in results if r['label']==1})},results=results)
 (root/'reports/clone-baseline-val.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report['metrics'],flush=True)
if __name__=='__main__':main()
