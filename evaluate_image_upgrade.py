"""Fixed-default comparison of actual 2026 image candidate and active Smaug.
Mirage rows are test-only and may never be used to fit thresholds/weights.
"""
import bootstrap,argparse,json,time,hashlib,math,gc
from pathlib import Path
from PIL import Image
ROOT=bootstrap.ROOT
def main():
 p=argparse.ArgumentParser();p.add_argument('--engine',choices=['omniaid','smaug'],required=True);args=p.parse_args();cohorts={}
 old=json.loads((ROOT/'reports/image-regions-comparison.json').read_text(encoding='utf-8'))['results'];cohorts['old_validation']=[r for r in old if r['split']=='val'];cohorts['mirage_test']=json.loads((ROOT/'data/mirage-check/manifest.json').read_text(encoding='utf-8'))
 progress=ROOT/f'reports/{args.engine}-upgrade-progress.json';saved=json.loads(progress.read_text(encoding='utf-8')) if progress.exists() else [];done={(r['cohort'],r['path']) for r in saved}
 import torch
 torch.set_num_threads(2)
 if args.engine=='omniaid':
  from omniaid_candidate import load,predict
  model=load();score=lambda image:predict(model,image)
 else:
  import sys,importlib.util
  sys.path.insert(0,str(ROOT/'runtime/smaug-packages'))
  import transformers.utils.import_utils as iu
  import transformers.utils as tu
  iu.is_torchaudio_available=lambda:False;tu.is_torchaudio_available=lambda:False
  spec=importlib.util.spec_from_file_location('smaug_checked_upgrade',ROOT/'vendor/smaug/smaug_image_detect.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);model=module.SmaugImageDetect.from_pretrained(str(ROOT/'models/smaug'));score=lambda image:model(image,batch_size=3)
 for cohort,rows in cohorts.items():
  for i,row in enumerate(rows):
   if (cohort,row['path']) in done:continue
   started=time.monotonic()
   with Image.open(ROOT/row['path']) as image:
    value=float(score(image.convert('RGB')))
   if not math.isfinite(value) or not 0<=value<=1:raise RuntimeError('Nonfinite model output')
   saved.append(dict(row,cohort=cohort,score=value,predicted=int(value>=.5),seconds=time.monotonic()-started));temp=progress.with_suffix('.new');temp.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(progress)
   if i%10==0:print(args.engine,cohort,i+1,'/',len(rows),flush=True)
 del model;gc.collect();torch.cuda.empty_cache()
 from check_recent_model import statistics
 from sklearn.metrics import roc_auc_score
 report=dict(engine=args.engine,threshold=.5,protocol='Author default decision threshold fixed before new test. Old80 validation follow-up; Mirage240 test-only, no threshold/head fit.',metrics={cohort:statistics([r for r in saved if r['cohort']==cohort]) for cohort in cohorts},auc={cohort:float(roc_auc_score([r['label'] for r in saved if r['cohort']==cohort],[r['score'] for r in saved if r['cohort']==cohort])) for cohort in cohorts},by_generator={},results=saved,limitations=['Mirage author benchmark, locally unseen; upstream pretraining overlap unknown.','Six photorealistic generator sources, four content types; no GPT-wide or universal accuracy claim.','Author image labels used; not independent manual authentication of every real photo.'])
 fresh=[r for r in saved if r['cohort']=='mirage_test']
 for generator in sorted({r['generator'] for r in fresh if r['label']==1}):report['by_generator'][generator]=statistics([r for r in fresh if r['label']==0 or r['generator']==generator])
 (ROOT/f'reports/{args.engine}-upgrade-comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report['metrics'],flush=True)
if __name__=='__main__':main()
