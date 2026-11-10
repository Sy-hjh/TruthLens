"""Fresh source-group test protocol. Downloads do not train or tune any model."""
import bootstrap,json,csv,io,random,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collect_domain_cases import get
ROOT=bootstrap.ROOT

def main():
 folder=ROOT/'data/video-final';folder.mkdir(exist_ok=True);planfile=folder/'planned.json';repo='kontur-ai/rtfs-10k';rev='83063ae33220e8da968587d4365bd986c7005835';base=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/'
 if planfile.exists():planned=json.loads(planfile.read_text())['rows']
 else:
  tables={g:list(csv.DictReader(io.StringIO(get(base+g+'.csv').text))) for g in ('inswapper','uniface')};matched={g:{} for g in tables}
  for g,items in tables.items():
   for row in items:
    if row['success'].lower()=='true':matched[g].setdefault(row['video'],row)
  previous=[]
  for name in ['data/video-fit/manifest.json','data/video-release-check/manifest.json','reports/video-diagnostic-progress.json']:previous.extend(json.loads((ROOT/name).read_text()))
  used={Path(r['group']).stem.rsplit('_',2)[0] for r in previous};videos=sorted(set(matched['inswapper'])&set(matched['uniface']));random.Random(263).shuffle(videos);selected=[]
  for video in videos:
   identity,start,end=Path(video).stem.rsplit('_',2)
   if identity in used or int(end)-int(start)>12:continue
   used.add(identity);selected.append(video)
   if len(selected)==100:break
  if len(selected)<80:raise RuntimeError('Insufficient fresh source IDs')
  planned=[]
  for video in selected:
   planned.append(dict(remote='original_videos/'+video,label=0,group=video,generator='none'))
   for g in ('inswapper','uniface'):planned.append(dict(remote=g+'/'+matched[g][video]['filename'],label=1,group=video,generator=g))
  planfile.write_text(json.dumps(dict(repo=repo,revision=rev,license='cc-by-sa-4.0',note='Fresh source YouTube IDs; previous training, validation and observed diagnostics excluded. Actor identity separation not verified. No training in this script.',source_ids=len(selected),rows=planned),indent=2))
 def fetch(row):
  target=folder/Path(row['remote']).name
  if not target.exists():
   data=get(base+row['remote']).content;tmp=target.with_suffix('.part');tmp.write_bytes(data);tmp.replace(target)
  return dict(row,path=target.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
 rows=[]
 with ThreadPoolExecutor(max_workers=4) as pool:
  for row in pool.map(fetch,planned):
   rows.append(row)
   if len(rows)%20==0:print('Fresh source final-test download',len(rows),'/',len(planned),flush=True)
 (folder/'manifest.json').write_text(json.dumps(rows,indent=2));print('Fresh locked source test ready',len(rows))
if __name__=='__main__':main()
