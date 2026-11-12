"""Create a reviewable source bundle, excluding private/runtime/large model data."""
import bootstrap,json,zipfile,hashlib
from pathlib import Path
ROOT=bootstrap.ROOT

def main():
 target=ROOT/'submission/亲安_参赛源码包.zip';items=[]
 for path in ROOT.iterdir():
  if path.is_file() and (path.suffix in ('.py','.ps1','.cmd','.md','.txt') or path.name in ('.gitignore','.gitattributes','.env.example','team.json')):items.append(path)
 for folder in ('backend','web','frontend','frontend-next','vendor','docs','release'):
  for path in (ROOT/folder).rglob('*'):
   if not path.is_file() or any(x in path.parts for x in ('node_modules','__pycache__','.git')) or path.suffix in ('.pyc','.tsbuildinfo'):continue
   if path.suffix.lower() in ('.safetensors','.onnx','.pth') or (path.suffix=='.pt' and folder!='release'):continue
   items.append(path)
 for path in (ROOT/'data/demo').iterdir():
  if path.suffix in ('.mp3','.json'):items.append(path)
 # Small locally trained experimental classifier, not large upstream encoders.
 for name in ('config.json','weights.npz'):
  path=ROOT/'models/text-patterns'/name
  if path.exists():items.append(path)
 # Public benchmark summaries only; no original images, videos or per-user rows.
 public=json.loads((ROOT/'docs/benchmarks.json').read_text(encoding='utf-8'))['reports']
 # Never package a partial evaluation after an interrupted experiment.
 for filename,cohort in [('gend-final.json','fresh180'),('smaug-whole-final.json','whole_image_test')]:
  assert public[filename][cohort]['metrics']['n']>0,'Final evaluation is incomplete: '+filename
 assert all(public['verispoof-test-channels.json'][channel]['metrics']['n']==624 for channel in ('clean','aac32','phone8')),'Acoustic final test is incomplete'
 assert public['voice-data-audit.json']['pending_test_downloads']==0,'Acoustic audit is incomplete'
 with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
  for path in sorted(set(items)):archive.write(path,'qinan/'+path.relative_to(ROOT).as_posix())
  for name,value in public.items():archive.writestr('qinan/reports/'+name,json.dumps(value,ensure_ascii=False,indent=2))
  for name in ('delivery-verification.json','deployment-http.json','voice-browser-acceptance.json','chat-pipeline-check.json','demo-video-check.json','backend-checks-final.json','report-trace-check.json','chat-user-fixed-acceptance.json'):
   if name in public:continue
   archive.write(ROOT/'reports'/name,'qinan/reports/'+name)
  for name in ('text-pattern-training.json','text-semantic-comparison.json','audio-nuisance-check.json','text-upgrade-acceptance.json','image-regions-comparison.json','ftcn-contiguous-comparison.json','new-model-check.json','omniaid-reference-equivalence.json','ordered-temporal-head-training.json','ordered-temporal-head-test.json','ordered-head-active-baseline.json','ordered-delivery-parity.json','av-author-sample-check.json','eight-demo-v2-changed-checks.json'):
   path=ROOT/'reports'/name
   if path.exists() and name not in public:archive.write(path,'qinan/reports/'+name)
 with zipfile.ZipFile(target) as archive:
  names=archive.namelist();assert not any('/runtime/' in n or '/node_modules/' in n or 'user-regression' in n or 'cases.sqlite' in n or n.endswith('.mp4') for n in names)
  assert len(names)==len(set(names)),'Duplicate archive paths'
  assert archive.testzip() is None
 manifest=dict(file=target.name,bytes=target.stat().st_size,sha256=hashlib.sha256(target.read_bytes()).hexdigest(),files=len(names),excluded='Private images, contacts, history DB, raw training/test media, node_modules, large pretrained weights; no public publishing performed.')
 (ROOT/'submission/源码包校验.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print(manifest)
if __name__=='__main__':main()
