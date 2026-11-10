"""Pinned, hash-verified research model installer. No environment upgrades."""
import bootstrap,json,hashlib
from collect_domain_cases import get
from range_stream import RangeStream
from pathlib import Path

def main():
 repo='eliya/forensics_0.3B_xlsr_wild_deepfake_classifier';rev='0cbc87b3fbd683ff8c8c961bcf244a8d5f1bcf02';p=bootstrap.ROOT/'models/audio-forensics';p.mkdir(exist_ok=True)
 meta=get(f'https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true').json();f=next(x for x in meta['siblings'] if x['rfilename']=='checkpoint_epoch_4.safetensors');expected=f['lfs']['sha256'];path=p/'checkpoint_epoch_4.safetensors'
 if not path.exists():
  temp=p/'download.part';size=f['size'];print('Downloading',size,flush=True)
  with RangeStream(f'https://huggingface.co/{repo}/resolve/{rev}/checkpoint_epoch_4.safetensors',size,workers=16) as stream,temp.open('wb') as out:
   while data:=stream.read(4*1024*1024):out.write(data);print(out.tell(),'/',size,flush=True)
  if hashlib.sha256(temp.read_bytes()).hexdigest()!=expected:raise RuntimeError('Weight hash mismatch')
  temp.replace(path)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
 (p/'source.json').write_text(json.dumps(dict(repo=repo,revision=rev,sha256=expected,license='cc-by-nc-4.0',purpose='research speech synthesis diagnostic; verify Mandarin performance locally'),indent=2),encoding='utf-8')
 print('Verified',path.stat().st_size)
if __name__=='__main__':main()
