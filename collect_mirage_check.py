"""Predeclared 240-image modern TEST-ONLY check; never train or tune on it."""
import bootstrap,json,hashlib,requests,time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
ROOT=bootstrap.ROOT;REPO='Yunncheng/Mirage-Test';REV='820a191bb0844ae74a1bd9eb57b28268257a4053'
def main():
 folder=ROOT/'data/mirage-check';folder.mkdir(exist_ok=True);meta=json.loads((ROOT/'runtime/mirage-test-meta.json').read_text());plan=folder/'planned.json'
 if plan.exists():rows=json.loads(plan.read_text(encoding='utf-8'))['rows']
 else:
  rows=[]
  for category in ['Animal','Human','Object','Scene']:
   real=[r for r in meta['siblings'] if r['rfilename'].startswith(category+'/0_real/')];fake=[r for r in meta['siblings'] if r['rfilename'].startswith(category+'/1_fake/')]
   rank=lambda r:hashlib.sha256(('qinan-modern-image-check-20261112/'+r['rfilename']).encode()).hexdigest()
   generators=sorted({r['rfilename'].split('/')[2] for r in fake});selected=[]
   for generator in generators:selected.extend(sorted([r for r in fake if r['rfilename'].split('/')[2]==generator],key=rank)[:5])
   selected.extend(sorted(real,key=rank)[:len(selected)])
   for item in selected:
    remote=item['rfilename'];label=int('/1_fake/' in remote);rows.append(dict(remote=remote,label=label,category=category,generator=remote.split('/')[2] if label else 'real',bytes=item['size'],expected_sha256=item.get('lfs',{}).get('sha256')))
  plan.write_text(json.dumps(dict(repo=REPO,revision=REV,protocol='Fixed SHA ordering; five per fake generator/category and matched real counts. All test-only; no calibration or training. Anime excluded because it has no real controls.',rows=rows),ensure_ascii=False,indent=2),encoding='utf-8')
 def fetch(row):
  target=folder/(hashlib.sha256(row['remote'].encode()).hexdigest()+Path(row['remote']).suffix)
  if not target.exists():
   for attempt in range(5):
    try:
     response=requests.get(f'https://huggingface.co/datasets/{REPO}/resolve/{REV}/{row["remote"]}?download=true',timeout=(20,90));response.raise_for_status();data=response.content
     if len(data)!=row['bytes']:raise ValueError('Incomplete image')
     if row['expected_sha256'] and hashlib.sha256(data).hexdigest()!=row['expected_sha256']:raise ValueError('Image checksum mismatch')
     temp=target.with_suffix('.part');temp.write_bytes(data);temp.replace(target);break
    except (requests.RequestException,ValueError):
     if attempt==4:raise
     time.sleep(attempt+1)
  digest=hashlib.sha256(target.read_bytes()).hexdigest();return dict(row,path=target.relative_to(ROOT).as_posix(),sha256=digest)
 output=[]
 with ThreadPoolExecutor(max_workers=6) as pool:
  for result in pool.map(fetch,rows):
   output.append(result);(folder/'manifest.partial.json').write_text(json.dumps(output,ensure_ascii=False),encoding='utf-8')
   if len(output)%12==0:print('Modern images',len(output),'/',len(rows),flush=True)
 seen={};clean=[];duplicates=[]
 for row in output:
  if row['sha256'] in seen:
   if seen[row['sha256']]!=row['label']:raise RuntimeError('Contradictory duplicate labels')
   duplicates.append(row['remote']);continue
  seen[row['sha256']]=row['label'];clean.append(row)
 (folder/'manifest.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding='utf-8');(folder/'source.json').write_text(json.dumps(dict(repo=REPO,revision=REV,license='MIT per author dataset card; source-image terms also apply',planned=len(rows),usable=len(clean),duplicates=duplicates,training_used=False,scope='Author test-only benchmark; locally unseen, not proof of no upstream pretraining overlap; no GPT-specific claim'),indent=2),encoding='utf-8');print('Ready',len(clean),flush=True)
if __name__=='__main__':main()
