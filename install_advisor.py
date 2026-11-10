"""Pinned local Chinese explanation model; no cloud prompts or paid API."""
import bootstrap,json,hashlib
from range_stream import RangeStream
from collect_domain_cases import get

def main():
 repo='Qwen/Qwen3-0.6B';folder=bootstrap.ROOT/'models/advisor';folder.mkdir(exist_ok=True)
 source=folder/'source.json'
 if source.exists():rev=json.loads(source.read_text())['revision']
 else:rev=get('https://huggingface.co/api/models/'+repo).json()['sha']
 meta=get(f'https://huggingface.co/api/models/{repo}/revision/{rev}?blobs=true').json();files=['config.json','generation_config.json','tokenizer.json','tokenizer_config.json','model.safetensors','README.md','LICENSE'];hashes={}
 for name in files:
  item=next(x for x in meta['siblings'] if x['rfilename']==name);path=folder/name
  if not path.exists():
   if item['size']>20*1024*1024:
    temp=folder/(name+'.part')
    offset=temp.stat().st_size if temp.exists() else 0
    with RangeStream(f'https://huggingface.co/{repo}/resolve/{rev}/{name}',item['size'],workers=8,start=offset) as stream,temp.open('ab') as out:
     while data:=stream.read(4*1024*1024):out.write(data);print(name,out.tell(),'/',item['size'],flush=True)
    if hashlib.sha256(temp.read_bytes()).hexdigest()!=item['lfs']['sha256']:raise RuntimeError('Advisor model hash mismatch')
    temp.replace(path)
   else:path.write_bytes(get(f'https://huggingface.co/{repo}/resolve/{rev}/{name}').content)
  hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
 source.write_text(json.dumps(dict(repo=repo,revision=rev,license='Apache-2.0',sha256=hashes,purpose='local sourced explanation only; never judges identity or authorizes payments'),indent=2),encoding='utf-8');print('Advisor model verified')
if __name__=='__main__':main()
