"""Pinned modern acoustic forensic model; resumable downloads, no remote code execution."""
import bootstrap,json,hashlib,requests
from urllib.parse import urlparse
from collect_domain_cases import get
from range_stream import RangeStream
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(8*1024*1024):h.update(chunk)
 return h.hexdigest()
def main():
 root=bootstrap.ROOT;repo='AustinXiao/VeriSpoof-Plus';rev='ef5b12112da17e0949b5e19fe0f9f198c9570fd9'
 meta=json.loads((root/'vendor/verispoof/metadata.json').read_text());folder=root/'models/verispoof';folder.mkdir(exist_ok=True);hashes={}
 for entry in meta['siblings']:
  name=entry['rfilename']
  if name.startswith('assets/') or name.startswith('.') or name.startswith('code/'):continue
  path=folder/name;path.parent.mkdir(exist_ok=True);url=f'https://huggingface.co/{repo}/resolve/{rev}/{name}?download=true'
  expected=entry.get('lfs',{}).get('sha256')
  if expected:
   if not path.exists():
    temp=path.with_suffix('.part');offset=temp.stat().st_size if temp.exists() else 0
    print('Downloading',name,entry['size'],'resume',offset,flush=True)
    probe=requests.get(url,headers={'Range':'bytes=0-0'},stream=True,timeout=(15,30));probe.raise_for_status();cdn=probe.url;probe.close()
    if not urlparse(cdn).hostname.endswith(('.hf.co','.huggingface.co')):raise RuntimeError('Unexpected model CDN')
    with RangeStream(cdn,entry['size'],workers=32,start=offset) as stream,temp.open('ab') as out:
     while chunk:=stream.read(8*1024*1024):
      out.write(chunk)
      if out.tell()%(64*1024*1024)==0:print(name,out.tell(),'/',entry['size'],flush=True)
    if digest(temp)!=expected:raise RuntimeError('Weight hash mismatch: '+name)
    temp.replace(path)
   if digest(path)!=expected:raise RuntimeError('Weight hash mismatch: '+name)
  elif not path.exists():path.write_bytes(get(url).content)
  hashes[name]=digest(path)
 config=folder/'audio-config';config.mkdir(exist_ok=True);cfg_rev='bcd2b5b7f32b480ab5790554cfa8347f246a14f3'
 for name in ['config.json','processor_config.json']:
  path=config/name
  if not path.exists():path.write_bytes(get(f'https://huggingface.co/Qwen/Qwen3-ASR-1.7B-hf/resolve/{cfg_rev}/{name}').content)
 feature=json.loads((config/'processor_config.json').read_text())['feature_extractor'];(config/'preprocessor_config.json').write_text(json.dumps(feature))
 (config/'source.json').write_text(json.dumps(dict(repo='Qwen/Qwen3-ASR-1.7B-hf',revision=cfg_rev,purpose='Architecture and mel filter config only; no ASR transcription'),indent=2))
 for path in config.iterdir():
  if path.is_file():hashes['audio-config/'+path.name]=digest(path)
 (folder/'source.json').write_text(json.dumps(dict(repo=repo,revision=rev,license='CC-BY-NC-4.0 model; Apache-2.0 code; retain NOTICE',sha256=hashes),indent=2))
 print('Verified VeriSpoof files',len(hashes),flush=True)
if __name__=='__main__':main()
