"""Pinned Mandarin reference-cloning pairs, speaker-disjoint local splits. Not generic TTS."""
import bootstrap,json,hashlib,random,requests,time
import pyarrow.parquet as pq
from concurrent.futures import ThreadPoolExecutor
from collect_domain_cases import get
ROOT=bootstrap.ROOT
def main():
 folder=ROOT/'data/clone-bench';folder.mkdir(exist_ok=True);repo='Nanboy/RVCBench-Cloned-Speech';revision='365897b08925e241672731f25bcb5edc5857417f'
 if not (folder/'metadata.json').exists():(folder/'metadata.json').write_text(json.dumps(get(f'https://huggingface.co/api/datasets/{repo}/revision/{revision}').json()))
 meta=json.loads((folder/'metadata.json').read_text())
 if meta['sha']!=revision:raise RuntimeError('Dataset revision changed; use an isolated new experiment')
 for name in ['data/metadata.parquet','README.md','NOTICE']:
  path=folder/name.split('/')[-1]
  if not path.exists():path.write_bytes(get(f'https://huggingface.co/datasets/{repo}/resolve/{revision}/{name}').content)
 for entry in meta['siblings']:
  name=entry['rfilename']
  if name.startswith('LICENSES/') or name=='LICENSE':
   path=folder/name;path.parent.mkdir(parents=True,exist_ok=True)
   if not path.exists():path.write_bytes(get(f'https://huggingface.co/datasets/{repo}/resolve/{revision}/{name}').content)
 source=[r for r in pq.read_table(folder/'metadata.parquet').to_pylist() if r['language']=='zh' and r['condition']=='clean']
 speakers=sorted({r['speaker_id'] for r in source});random.Random(5147).shuffle(speakers)
 splits={s:'test' if i<6 else 'val' if i<12 else 'train' for i,s in enumerate(speakers)}
 rows=[];real={}
 for r in source:
  common=dict(speaker=r['speaker_id'],pair=r['pair_id'],text=r['text'],split=splits[r['speaker_id']],language='zh')
  rows.append(dict(common,remote='data/'+r['file_name'],label=1,generator=r['model'],published_sha256=r['sha256']))
  real.setdefault(r['ground_truth_file_name'],dict(common,remote='data/'+r['ground_truth_file_name'],label=0,generator='human'))
 rows+=list(real.values());rows.sort(key=lambda r:({'val':0,'train':1,'test':2}[r['split']],r['label'],r['pair'],r['generator']))
 (folder/'planned.json').write_text(json.dumps(dict(repo=repo,revision=revision,license='CC-BY-NC-4.0 plus generator-specific terms; retain NOTICE',speaker_splits=splits,rows=rows),ensure_ascii=False,indent=2),encoding='utf-8')
 (folder/'audio').mkdir(exist_ok=True)
 def fetch(row):
  name=hashlib.sha256(row['remote'].encode()).hexdigest()+'.wav';target=folder/'audio'/name
  if not target.exists():
   last=None
   for attempt in range(6):
    host='huggingface.co' if attempt<3 else 'hf-mirror.com'
    try:
     response=requests.get(f'https://{host}/datasets/{repo}/resolve/{revision}/'+row['remote']+'?download=true',timeout=(10,30));response.raise_for_status();data=response.content
     if row.get('published_sha256') and hashlib.sha256(data).hexdigest()!=row['published_sha256']:raise ValueError('Published sample hash mismatch')
     break
    except (requests.RequestException,ValueError) as e:last=e;print('Retry audio',attempt+1,row['remote'],type(e).__name__,flush=True);time.sleep(min(2**attempt,15))
   else:raise last
   temp=target.with_suffix('.part');temp.write_bytes(data);temp.replace(target)
  digest=hashlib.sha256(target.read_bytes()).hexdigest()
  if row.get('published_sha256') and digest!=row['published_sha256']:raise RuntimeError('Sample hash mismatch')
  return dict(row,path=target.relative_to(ROOT).as_posix(),sha256=digest)
 result=[]
 with ThreadPoolExecutor(max_workers=16) as pool:
  for r in pool.map(fetch,rows):
   result.append(r)
   if len(result)%50==0:
    progress=folder/'manifest-progress.tmp';progress.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');
    for retry in range(50):
     try:progress.replace(folder/'manifest.partial.json');break
     except PermissionError:time.sleep(.1)
    else:print('Progress manifest busy; verified audio files retained',flush=True)
    print('Mandarin clone pairs',len(result),'/',len(rows),r['split'],flush=True)
 temp=folder/'manifest-complete.tmp';temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(folder/'manifest.json')
 print('Complete',len(result),'real',len(real),'cloned',len(source),'speakers',len(speakers),flush=True)
 from audit_voice_data import audit
 audit()
if __name__=='__main__':main()
