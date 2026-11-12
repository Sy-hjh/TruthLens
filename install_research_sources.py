"""Restore pinned official candidate sources (no unknown mirror, no model code run)."""
import bootstrap,json,hashlib,argparse,requests
from bootstrap import ROOT
SOURCES={
 'fakestormer':('10Ring/FakeSTormer','c5b5f75100b878212a192c00013275f275f86182',['models/networks/backbones/vit.py','LICENSE','NOTICE']),
 'omniaid':('yunncheng/OmniAID','5217acb525892c33f5a30cdf96d37f08f008a164',['reward/omniaid.py','reward/clean_test.py','reward/README.md','models/OmniAID.py','data/datasets.py','LICENSE'])}
def restore(engine):
 repo,commit,files=SOURCES[engine];response=requests.get(f'https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1',timeout=40);response.raise_for_status();tree=response.json();assert not tree.get('truncated');lookup={r['path']:r for r in tree['tree']}
 for name in files:
  if name not in lookup:
   if name=='NOTICE':continue
   raise RuntimeError('Required author source missing: '+name)
  path=ROOT/'runtime'/(engine+'-source')/name
  if not path.exists():
   response=requests.get(f'https://raw.githubusercontent.com/{repo}/{commit}/{name}',timeout=40);response.raise_for_status();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(response.content)
  content=path.read_bytes();assert hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()==lookup[name]['sha'],name+' differs from fixed author commit'
 (ROOT/'runtime'/(engine+'-tree.json')).write_text(json.dumps(tree),encoding='utf-8');print('Pinned official source verified',engine,flush=True)
 if engine=='omniaid':
  folder=ROOT/'models/omniaid';folder.mkdir(exist_ok=True);repo='openai/clip-vit-large-patch14-336';revision='ce19dc912ca5cd21c8a653c79e251e808ccabcd1';sha='51b1c14aabcdf639c4a0370eeda1010b773bbe1df78319c7d0f5882c22ac0ac0';target=folder/'clip-config.json'
  if not target.exists():
   response=requests.get(f'https://huggingface.co/{repo}/resolve/{revision}/config.json',timeout=40);response.raise_for_status();target.write_bytes(response.content)
  assert hashlib.sha256(target.read_bytes()).hexdigest()==sha
  (folder/'backbone-source.json').write_text(json.dumps(dict(repo=repo,revision=revision,sha256=sha)),encoding='utf-8')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--engine',choices=list(SOURCES),required=True);restore(parser.parse_args().engine)
