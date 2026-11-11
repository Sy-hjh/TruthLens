"""Resume per-file frozen-encoder extraction; labels never enter acoustic encoders."""
import bootstrap,json,time,argparse
import numpy as np,torch
from backend.voice_forensics import load_model
from voice_features import ROOT,cache_folder,cache_path,audio,variants,features
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--watch',action='store_true');args=parser.parse_args();folder=cache_folder();folder.mkdir(parents=True,exist_ok=True)
 model=load_model();device='cuda' if torch.cuda.is_available() else 'cpu'
 while True:
  manifest=ROOT/'data/clone-bench/manifest.json';complete=manifest.exists()
  if not complete:manifest=manifest.with_name('manifest.partial.json')
  rows=[r for r in json.loads(manifest.read_text(encoding='utf-8')) if r['split'] in ('train','val')];pending=[r for r in rows if not cache_path(r).exists()]
  if pending:
   model.to(device)
   for i,row in enumerate(pending):
    f=features(model,variants(audio(ROOT/row['path'])),device);temp=cache_path(row).with_suffix('.partial.npy');np.save(temp,f);temp.replace(cache_path(row))
    if i%20==0:print('Frozen audio cache',i+1,'/',len(pending),'cached',len(list(folder.glob('*.npy'))),flush=True)
    if (folder/'STOP').exists():print('Stopped; every completed file is reusable',flush=True);return
   model.cpu()
   if device=='cuda':torch.cuda.empty_cache()
  if complete or not args.watch:break
  print('Waiting for further dataset downloads; cached features retained',flush=True);time.sleep(5)
 print('Feature cache ready',len(rows),'files, 3 matched channel variants each',flush=True)
if __name__=='__main__':main()
