"""Fixed benign recording-condition controls, inspired by thesis ch3/ch5; not an attack search."""
import bootstrap,json,random,numpy as np
from voice_features import audio
from verispoof_local import load
from backend.acoustic_protocol import analyze
ROOT=bootstrap.ROOT
def trim_edges(x):
 n=320;usable=len(x)//n
 if not usable:return x
 frames=x[:usable*n].reshape(-1,n);rms=np.sqrt((frames**2).mean(1));active=np.flatnonzero(rms>max(.001,float(rms.max())*.03))
 if not len(active):return x
 start=max(0,int(active[0])*n-1600);end=min(len(x),(int(active[-1])+1)*n+1600)
 return x[start:end] if end-start>=16000 else x
def main():
 rows=json.loads((ROOT/'data/clone-bench/manifest-audited.json').read_text(encoding='utf-8'));selected=[]
 for label in [0,1]:
  pool=sorted((r for r in rows if r['split']=='test' and r['label']==label),key=lambda r:r['sha256']);selected+=pool[:8]
 model=load();results=[]
 for i,row in enumerate(selected):
  x=audio(ROOT/row['path']);variants={'original':x,'edge_trim':trim_edges(x),'half_volume':x*.5,'fixed_silence':np.pad(x,(8000,8000))};values={}
  for name,y in variants.items():
   parts=analyze(model,y);score=max(p['score'] for p in parts);values[name]=dict(score=score,predicted=int(score>=.5))
  results.append(dict(sha256=row['sha256'],label=row['label'],generator=row['generator'],values=values));print(i+1,len(selected),values,flush=True)
 out=dict(scope='16 previously observed recordings; fixed identical benign changes for both labels; no optimized perturbations, no new independent accuracy claim.',recordings=len(results),decisions_flipped={v:sum(r['values'][v]['predicted']!=r['values']['original']['predicted'] for r in results) for v in ['edge_trim','half_volume','fixed_silence']},results=results)
 (ROOT/'reports/audio-nuisance-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
