"""Fixed official Chinese BERT for frozen text features; no remote model code."""
import bootstrap,json,hashlib,requests
from range_stream import RangeStream
from collect_domain_cases import get
ROOT=bootstrap.ROOT;REPO='google-bert/bert-base-chinese';REV='8f23c25b06e129b6c986331a13d8d025a92cf0ea'
def main():
 folder=ROOT/'models/text-encoder';folder.mkdir(exist_ok=True);meta=get(f'https://huggingface.co/api/models/{REPO}/revision/{REV}?blobs=true').json();hashes={}
 for name in ['config.json','tokenizer.json','tokenizer_config.json','vocab.txt','README.md','model.safetensors']:
  entry=next(e for e in meta['siblings'] if e['rfilename']==name);path=folder/name;url=f'https://huggingface.co/{REPO}/resolve/{REV}/{name}?download=true'
  if not path.exists():
   if name.endswith('.safetensors'):
    temp=path.with_suffix('.part');offset=temp.stat().st_size if temp.exists() else 0
    probe=requests.get(url,headers={'Range':'bytes=0-0'},stream=True,timeout=30);probe.raise_for_status();cdn=probe.url;probe.close()
    with RangeStream(cdn,entry['size'],workers=16,start=offset) as stream,temp.open('ab') as out:
     while block:=stream.read(8*1024*1024):out.write(block);print(name,out.tell(),'/',entry['size'],flush=True)
    assert hashlib.sha256(temp.read_bytes()).hexdigest()==entry['lfs']['sha256'];temp.replace(path)
   else:path.write_bytes(get(url).content)
  hashes[name]=hashlib.sha256(path.read_bytes()).hexdigest()
  if entry.get('lfs'):assert hashes[name]==entry['lfs']['sha256']
 (folder/'source.json').write_text(json.dumps(dict(repo=REPO,revision=REV,license='Apache-2.0 per official model card',sha256=hashes),indent=2),encoding='utf-8');print('Verified text encoder')
if __name__=='__main__':main()
