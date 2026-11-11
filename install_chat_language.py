"""Pinned larger local screenshot interpreter; resumable verified official weights."""
import bootstrap,json,hashlib,requests
from pathlib import Path
from range_stream import RangeStream
from collect_domain_cases import get
ROOT=bootstrap.ROOT
REPO='Qwen/Qwen3-1.7B';REV='70d244cc86ccca08cf5af4e1e306ecf908b1ad5e'
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(8*1024*1024):h.update(chunk)
 return h.hexdigest()
def main():
 folder=ROOT/'models/chat-language';folder.mkdir(exist_ok=True)
 meta=get(f'https://huggingface.co/api/models/{REPO}/revision/{REV}?blobs=true').json();hashes={}
 names=['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','model.safetensors.index.json','README.md','LICENSE']+[e['rfilename'] for e in meta['siblings'] if e['rfilename'].endswith('.safetensors')]
 for name in names:
  entry=next(e for e in meta['siblings'] if e['rfilename']==name);path=folder/name;url=f'https://huggingface.co/{REPO}/resolve/{REV}/{name}?download=true'
  if not path.exists():
   if entry['size']>20*1024*1024:
    temp=path.with_suffix('.part');offset=temp.stat().st_size if temp.exists() else 0
    probe=requests.get(url,headers={'Range':'bytes=0-0'},stream=True,timeout=(15,30));probe.raise_for_status();cdn=probe.url;probe.close()
    from urllib.parse import urlparse
    if not urlparse(cdn).hostname.endswith(('.hf.co','.huggingface.co')):raise RuntimeError('Unexpected official weight CDN')
    with RangeStream(cdn,entry['size'],workers=32,start=offset) as stream,temp.open('ab') as out:
     while block:=stream.read(8*1024*1024):
      out.write(block)
      if out.tell()%(64*1024*1024)==0:print(name,out.tell(),'/',entry['size'],flush=True)
    if digest(temp)!=entry['lfs']['sha256']:raise RuntimeError('Chat weight hash mismatch')
    temp.replace(path)
   else:path.write_bytes(get(url).content)
  actual=digest(path)
  if entry.get('lfs') and actual!=entry['lfs']['sha256']:raise RuntimeError('Chat file hash mismatch')
  hashes[name]=actual
 (folder/'source.json').write_text(json.dumps(dict(repo=REPO,revision=REV,license='Apache-2.0',sha256=hashes,purpose='Local screenshot text interpretation only, not AI-text attribution'),indent=2),encoding='utf-8')
 print('Chat language weights verified',flush=True)
if __name__=='__main__':main()
