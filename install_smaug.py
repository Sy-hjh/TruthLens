"""Pinned, hash-verified research model installer. No environment upgrades."""
import bootstrap,json,hashlib
from collect_domain_cases import get
from range_stream import RangeStream
from pathlib import Path

def main():
 repo='abacusai/Smaug-AI-Image-Detector';rev='c7c95951e04a87b884a4ad479401b1128c3903bd';p=bootstrap.ROOT/'models/smaug';p.mkdir(exist_ok=True)
 meta=get(f'https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true').json();f=next(x for x in meta['siblings'] if x['rfilename']=='model.safetensors');expected=f['lfs']['sha256'];path=p/'model.safetensors'
 if not path.exists():
  temp=p/'download.part';size=f['size'];print('Downloading',size,flush=True)
  offset=temp.stat().st_size if temp.exists() else 0
  with RangeStream(f'https://huggingface.co/{repo}/resolve/{rev}/model.safetensors',size,workers=8,start=offset) as stream,temp.open('ab') as out:
   while data:=stream.read(4*1024*1024):out.write(data);print(out.tell(),'/',size,flush=True)
  if hashlib.sha256(temp.read_bytes()).hexdigest()!=expected:raise RuntimeError('Weight hash mismatch')
  temp.replace(path)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
 source=dict(repo=repo,revision=rev,sha256=expected,license='Apache-2.0 model card; upstream data terms separate',purpose='Whole-image generation candidate; not reliable local edit localization',files={})
 
 for name in ['config.json','README.md','LICENSE','modules.json','processor_config.json','sentence_bert_config.json','config_sentence_transformers.json','tokenizer.json','tokenizer_config.json','chat_template.jinja','1_Pooling/config.json','2_Normalize/config.json','3_Dense/config.json','3_Dense/model.safetensors']:
  (p/name).parent.mkdir(exist_ok=True);data=get(f'https://huggingface.co/{repo}/resolve/{rev}/{name}').content
  entry=next(x for x in meta['siblings'] if x['rfilename']==name)
  if entry.get('lfs') and hashlib.sha256(data).hexdigest()!=entry['lfs']['sha256']:raise RuntimeError('Auxiliary weight hash mismatch')
  (p/name).write_bytes(data);source['files'][name]=hashlib.sha256(data).hexdigest()
 (p/'source.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
 print('Verified',path.stat().st_size)
if __name__=='__main__':main()
