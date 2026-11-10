"""Pinned, hash-verified research model installer. No environment upgrades."""
import bootstrap,json,hashlib
from collect_domain_cases import get
from range_stream import RangeStream
from pathlib import Path

def main():
 repo='obuladinnesai/car-damage-photo-integrity-v9';rev='4b7b6ea59cc125119794b2f5a49efb966ec3e5ff';p=bootstrap.ROOT/'models/integrity-v9';p.mkdir(exist_ok=True)
 meta=get(f'https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true').json();f=next(x for x in meta['siblings'] if x['rfilename']=='model.safetensors');expected=f['lfs']['sha256'];path=p/'model.safetensors'
 if not path.exists():
  temp=p/'download.part';size=f['size'];print('Downloading',size,flush=True)
  with RangeStream(f'https://huggingface.co/{repo}/resolve/{rev}/model.safetensors',size,workers=8) as stream,temp.open('wb') as out:
   while data:=stream.read(4*1024*1024):out.write(data);print(out.tell(),'/',size,flush=True)
  if hashlib.sha256(temp.read_bytes()).hexdigest()!=expected:raise RuntimeError('Weight hash mismatch')
  temp.replace(path)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
 (p/'source.json').write_text(json.dumps(dict(repo=repo,revision=rev,sha256=expected,license='apache-2.0',purpose='research diagnostic only; car-domain model not validated on products'),indent=2),encoding='utf-8')
 print('Verified',path.stat().st_size)
if __name__=='__main__':main()
