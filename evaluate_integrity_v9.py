import bootstrap,json,sys,torch,time
from PIL import Image
from pathlib import Path
sys.path.insert(0,str(bootstrap.ROOT/'vendor/integrity_v9'))
from inference import load_model,score_image
from check_recent_model import statistics

def main():
 torch.set_num_threads(4)
 net,cfg,dev=load_model(str(bootstrap.ROOT/'models/integrity-v9/model.safetensors'),str(bootstrap.ROOT/'vendor/integrity_v9/config.json'),device='cpu')
 rows=json.loads((bootstrap.ROOT/'data/domain-cases/manifest.json').read_text(encoding='utf-8'));selected=[]
 for label in (0,1):
  groups=sorted(set(r['category'] for r in rows));selected.extend(r for category in groups for r in [x for x in rows if x['label']==label and x['category']==category][:5])
 results=[]
 for i,row in enumerate(selected):
  start=time.monotonic()
  with Image.open(bootstrap.ROOT/row['path']) as im:r=score_image(net,cfg,dev,im,condition='upload')
  results.append(dict(row,score=r['score'],threshold=r['threshold'],predicted=int(r['flagged']),seconds=time.monotonic()-start))
  (bootstrap.ROOT/'reports/integrity-v9-progress.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(i+1,'/',len(selected),round(r['score'],3),flush=True)
 report=dict(metrics=statistics(results),results=results,condition='author upload: max1600 JPEG85, original threshold4.193077',note='60 diagnostic product cases, not independent unseen release test; source car-domain model; raw score is not probability.')
 (bootstrap.ROOT/'reports/integrity-v9-diagnostic.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(report['metrics'])
if __name__=='__main__':main()
