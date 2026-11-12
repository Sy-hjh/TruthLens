"""Check inference-only adapter against author's full model; no threshold fitting."""
import bootstrap,json,gc
import torch
from PIL import Image
from omniaid_candidate import load,predict
from bootstrap import ROOT

def main():
 torch.set_num_threads(2)
 rows=json.loads((ROOT/'data/mirage-check/manifest.json').read_text(encoding='utf-8'))[:3]
 scores={}
 for implementation in ('clean','full'):
  model=load(implementation=implementation)
  scores[implementation]=[]
  for row in rows:
   with Image.open(ROOT/row['path']) as image:scores[implementation].append(predict(model,image))
  del model;gc.collect();torch.cuda.empty_cache()
 differences=[abs(a-b) for a,b in zip(scores['clean'],scores['full'])]
 report=dict(paths=[r['path'] for r in rows],scores=scores,max_absolute_difference=max(differences),passed=max(differences)<1e-5,scope='Numerical adapter equivalence only; no accuracy or threshold selection.')
 (ROOT/'reports/omniaid-reference-equivalence.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print(report,flush=True)
 assert report['passed'],'Author inference implementations differ; investigate before use'
if __name__=='__main__':main()
