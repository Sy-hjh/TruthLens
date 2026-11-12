"""New source-group test for the 2025 temporal candidate; no training or tuning."""
import bootstrap,json,csv,io,hashlib,random,argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collect_domain_cases import get
ROOT=bootstrap.ROOT;REV='83063ae33220e8da968587d4365bd986c7005835';REPO='kontur-ai/rtfs-10k'
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--cohort',choices=['video-temporal-check','video-temporal-head-test'],default='video-temporal-check');args=parser.parse_args()
 folder=ROOT/'data'/args.cohort;folder.mkdir(exist_ok=True);plan=folder/'planned.json';base=f'https://huggingface.co/datasets/{REPO}/resolve/{REV}/'
 if plan.exists():rows=json.loads(plan.read_text(encoding='utf-8'))['rows']
 else:
  used=set()
  def scan(value):
   if isinstance(value,dict):
    if isinstance(value.get('group'),str):used.add(Path(value['group']).stem.rsplit('_',2)[0])
    for child in value.values():
     if isinstance(child,(dict,list)):scan(child)
   elif isinstance(value,list):
    for child in value:scan(child)
  paths=list((ROOT/'data').glob('video*/manifest.json'))+list((ROOT/'data').glob('video*/planned.json'))
  paths += [p for p in (ROOT/'reports').glob('*.json') if p.name.startswith(('video-','sifta-','gend-','ftcn-'))]
  for path in paths:
   try:scan(json.loads(path.read_text(encoding='utf-8')))
   except (ValueError,UnicodeError):continue
  tables={}
  for generator in ['inswapper','uniface']:
   items=list(csv.DictReader(io.StringIO(get(base+generator+'.csv').text)));lookup={}
   for row in items:
    if row['success'].lower()=='true':lookup.setdefault(row['video'],row)
   tables[generator]=lookup
  videos=sorted(set(tables['inswapper'])&set(tables['uniface']));random.Random(20261112 if args.cohort=='video-temporal-check' else 2026111202).shuffle(videos);selected=[]
  for video in videos:
   identity,start,end=Path(video).stem.rsplit('_',2)
   if identity in used or int(end)-int(start)>12:continue
   used.add(identity);selected.append(video)
   if len(selected)==20:break
  if len(selected)!=20:raise RuntimeError('Insufficient locally unseen source groups')
  rows=[]
  for video in selected:
   rows.append(dict(remote='original_videos/'+video,label=0,group=video,generator='none'))
   for generator in tables:rows.append(dict(remote=generator+'/'+tables[generator][video]['filename'],label=1,group=video,generator=generator))
  plan.write_text(json.dumps(dict(repo=REPO,revision=REV,source_ids=20,license='CC-BY-SA-4.0 per source card',rows=rows,scope='Locally unseen source YouTube IDs; no claim of actor identity isolation or no pretraining overlap. Fixed before temporal predictions.'),indent=2),encoding='utf-8')
 def fetch(row):
  target=folder/Path(row['remote']).name
  if not target.exists():
   response=get(base+row['remote']);temp=target.with_suffix('.part');temp.write_bytes(response.content);temp.replace(target)
  return dict(row,path=target.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
 output=[]
 with ThreadPoolExecutor(max_workers=4) as pool:
  for row in pool.map(fetch,rows):
   output.append(row)
   if len(output)%6==0:print('New source video',len(output),'/',len(rows),flush=True)
 (folder/'manifest.json').write_text(json.dumps(output,indent=2),encoding='utf-8');print('New source-group test ready',len(output),flush=True)
if __name__=='__main__':main()
