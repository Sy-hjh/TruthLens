"""Pinned, hash-verified research model installer. No environment upgrades."""
import bootstrap,json,hashlib
from collect_domain_cases import get
from range_stream import RangeStream
from pathlib import Path

def main():
 repo='TensorFold/detectra-v1';rev='2bbc31161daa46932e05ee6f96e7016ee817bbde';p=bootstrap.ROOT/'models/detectra';p.mkdir(exist_ok=True)
 meta=get(f'https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true').json();f=next(x for x in meta['siblings'] if x['rfilename']=='model.safetensors');expected=f['lfs']['sha256'];path=p/'model.safetensors'
 if not path.exists():
  temp=p/'download.part';size=f['size'];print('Downloading',size,flush=True)
  offset=temp.stat().st_size if temp.exists() else 0
  with RangeStream(f'https://huggingface.co/{repo}/resolve/{rev}/model.safetensors',size,workers=8,start=offset) as stream,temp.open('ab') as out:
   while data:=stream.read(4*1024*1024):out.write(data);print(out.tell(),'/',size,flush=True)
  if hashlib.sha256(temp.read_bytes()).hexdigest()!=expected:raise RuntimeError('Weight hash mismatch')
  temp.replace(path)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
 (p/'source.json').write_text(json.dumps(dict(repo=repo,revision=rev,sha256=expected,license='MIT model card; upstream data terms separate',purpose='Modern-generator small vision candidate; test before deployment'),indent=2),encoding='utf-8')
 
 for name in ['README.md']:
  (p/name).write_bytes(get(f'https://huggingface.co/{repo}/resolve/{rev}/{name}').content)
 print('Verified',path.stat().st_size)
if __name__=='__main__':main()
