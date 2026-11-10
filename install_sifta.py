"""Pinned, hash-verified research model installer. No environment upgrades."""
import bootstrap,json,hashlib
from collect_domain_cases import get
from range_stream import RangeStream
from pathlib import Path

def main():
 repo='zodumair/sifta-deepfake-detector';rev='d551c5bb8763c06cef8a57a5f860537e3fbf35fc';p=bootstrap.ROOT/'models/sifta';p.mkdir(exist_ok=True)
 meta=get(f'https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true').json();f=next(x for x in meta['siblings'] if x['rfilename']=='model.safetensors');expected=f['lfs']['sha256'];path=p/'model.safetensors'
 if not path.exists():
  temp=p/'download.part';size=f['size'];print('Downloading',size,flush=True)
  with RangeStream(f'https://huggingface.co/{repo}/resolve/{rev}/model.safetensors',size,workers=16) as stream,temp.open('wb') as out:
   while data:=stream.read(4*1024*1024):out.write(data);print(out.tell(),'/',size,flush=True)
  if hashlib.sha256(temp.read_bytes()).hexdigest()!=expected:raise RuntimeError('Weight hash mismatch')
  temp.replace(path)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
 (p/'source.json').write_text(json.dumps(dict(repo=repo,revision=rev,sha256=expected,license='research only; upstream dataset restrictions',purpose='XCLIP face video diagnostic; no identity verification'),indent=2),encoding='utf-8')
 
 for name in ['sifta_config.json','xclip_config.json','README.md','DATA_CARD.md']:
  (p/name).write_bytes(get(f'https://huggingface.co/{repo}/resolve/{rev}/{name}').content)
 import shutil
 shutil.copyfile(bootstrap.ROOT/'models/face-detector/model.onnx',p/'face_detection_yunet_2023mar.onnx')
 print('Verified',path.stat().st_size)
if __name__=='__main__':main()
