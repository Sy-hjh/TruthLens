"""Compare official 3-view sampling with global + 3x3 regions; no automatic activation.
Fixed SHA-selected observed validation/test subsets. Follow-up, not a new accuracy claim.
"""
import bootstrap,sys,json,hashlib,time,importlib.util
from PIL import Image
import numpy as np,torch
sys.path.insert(0,str(bootstrap.ROOT/'runtime/smaug-packages'))
import transformers.utils.import_utils as iu
import transformers.utils as tu
iu.is_torchaudio_available=lambda:False;tu.is_torchaudio_available=lambda:False
from sentence_transformers import SentenceTransformer
from backend.image_regions import expanded_views
from check_recent_model import statistics
ROOT=bootstrap.ROOT
def main():
 torch.set_num_threads(2);device='cuda' if torch.cuda.is_available() else 'cpu';st=SentenceTransformer(str(ROOT/'models/smaug'),local_files_only=True,device=device,config_kwargs={'audio_config':None},model_kwargs={'torch_dtype':torch.bfloat16 if device=='cuda' else torch.float32})
 spec=importlib.util.spec_from_file_location('smaug_audited',ROOT/'vendor/smaug/smaug_image_detect.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.SmaugImageDetect(st)
 rows=json.loads((ROOT/'data/balanced-v1/manifest.json').read_text(encoding='utf-8'));selected=[]
 for split in ['val','test']:
  for label in [0,1]:
   subset=[r for r in rows if r['split']==split and r['label']==label]
   selected.extend(sorted(subset,key=lambda r:hashlib.sha256(r['path'].encode()).hexdigest())[:40])
 progress=ROOT/'reports/image-regions-comparison.partial.json';out=json.loads(progress.read_text()) if progress.exists() else [];done={r['path'] for r in out}
 for i,row in enumerate(selected):
  if row['path'] in done:continue
  started=time.monotonic()
  with Image.open(ROOT/row['path']) as image:
   image=image.convert('RGB');original=m.views(image,3);extra,trace=expanded_views(image);logits=[]
   for start in range(0,len(original+extra),3):
    with torch.inference_mode():logits.extend(st.encode([{'image':v} for v in (original+extra)[start:start+3]],batch_size=3,convert_to_tensor=True).float().view(-1).cpu().tolist())
  sigmoid=lambda v:float(torch.sigmoid(torch.tensor(v)))
  scores=dict(official3=sigmoid(np.mean(logits[:3])),global_only=sigmoid(logits[3]),grid9=sigmoid(np.mean(logits[4:])),global_grid10=sigmoid(np.mean(logits[3:])))
  out.append(dict(path=row['path'],label=row['label'],split=row['split'],scores=scores,view_count=len(extra),seconds=time.monotonic()-started));progress.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');print(i+1,'/',len(selected),row['split'],scores,flush=True)
 report=dict(scope='Predeclared SHA-selected 40 per class/split from previously observed balanced-v1. Same images for all strategies. Follow-up comparison, not fresh independent accuracy.',sampling='Official3 vs whole image vs 9 local regions (60% short side, resized528) vs mean of global+9. Additional crops may upscale and alter feature distribution.',counts={s:sum(r['split']==s for r in out) for s in ['val','test']},metrics={s:{method:statistics([dict(label=r['label'],predicted=int(r['scores'][method]>=.5)) for r in out if r['split']==s]) for method in ['official3','global_only','grid9','global_grid10']} for s in ['val','test']},results=out,active_changed=False)
 (ROOT/'reports/image-regions-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report['metrics'],flush=True)
if __name__=='__main__':main()
