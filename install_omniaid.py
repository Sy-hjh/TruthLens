"""Fixed author-published 2026 image detector candidate, local checkpoint only."""
import bootstrap,json,requests,hashlib
from range_stream import RangeStream
ROOT=bootstrap.ROOT;REPO='Yunncheng/OmniAID';REV='279cae7398ac6636f46fc4668f755f11210b36bf'
def main():
 folder=ROOT/'models/omniaid';folder.mkdir(exist_ok=True);response=requests.get(f'https://huggingface.co/api/models/{REPO}/revision/{REV}?blobs=true',timeout=40);response.raise_for_status();meta=response.json();files={}
 for name in ['ckpt/checkpoint_omniaid_v2.pth','config/config_omniaid_v2.json','README.md']:
  item=next(x for x in meta['siblings'] if x['rfilename']==name);target=folder/name.rsplit('/',1)[-1];url=f'https://huggingface.co/{REPO}/resolve/{REV}/{name}?download=true'
  if not target.exists():
   if name.endswith('.pth'):
    partial=target.with_suffix('.part');offset=partial.stat().st_size if partial.exists() else 0;r=requests.get(url,headers={'Range':'bytes=0-0'},stream=True,timeout=40);r.raise_for_status();cdn=r.url;r.close()
    with RangeStream(cdn,item['size'],workers=16,start=offset) as stream,partial.open('ab') as out:
     while block:=stream.read(8*1024*1024):out.write(block);out.flush();print(out.tell(),'/',item['size'],flush=True)
    assert hashlib.sha256(partial.read_bytes()).hexdigest()==item['lfs']['sha256'];partial.replace(target)
   else:
    r=requests.get(url,timeout=40);r.raise_for_status();target.write_bytes(r.content)
  digest=hashlib.sha256(target.read_bytes()).hexdigest()
  if item.get('lfs'):assert digest==item['lfs']['sha256']
  files[target.name]=digest
 (folder/'source.json').write_text(json.dumps(dict(repo=REPO,revision=REV,sha256=files,license='MIT per author card; upstream training data terms separate',purpose='2026 candidate, evaluate before activation'),indent=2),encoding='utf-8');print('Verified author OmniAID v2',flush=True)
if __name__=='__main__':main()
