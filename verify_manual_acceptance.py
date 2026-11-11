"""Run labelled controls through actual HTTP uploads; record misses without hiding them."""
import bootstrap,json,time,requests
ROOT=bootstrap.ROOT;BASE='http://127.0.0.1:8010'
def main():
 rows=json.loads((ROOT/'data/manual-acceptance/manifest.json').read_text(encoding='utf-8'));results=[]
 for i,row in enumerate(rows):
  with (ROOT/row['path']).open('rb') as f:r=requests.post(BASE+'/api/analyze',files={'file':('manual-control-'+str(i)+(ROOT/row['path']).suffix,f)},timeout=30)
  r.raise_for_status();key=r.json()['job_id']
  for _ in range(1200):
   job=requests.get(BASE+'/api/jobs/'+key,timeout=20).json()
   if job['status']!='processing':break
   time.sleep(.5)
  modules=job.get('result',{}).get('modules',{});kind=row.get('modality','image');m=modules.get(kind,{})
  scores=[x['score'] for x in m.get('segments',[])]+([m['score']] if 'score' in m else [])
  predicted=int(any(x['score']>=x.get('threshold',.5) for x in m.get('segments',[])) or ('score' in m and m['score']>=m.get('threshold',.5))) if scores else None
  results.append(dict(path=row['path'],label=row['label'],modality=kind,sha256=row['sha256'],status=job['status'],module_status=m.get('status'),score=max(scores) if scores else None,predicted=predicted,correct=predicted==row['label'],source=m.get('source'),provenance=row.get('provenance',row.get('source',row.get('source_url')))))
  requests.delete(BASE+'/api/cases/'+key,timeout=20).raise_for_status()
  (ROOT/'reports/manual-acceptance.json').write_text(json.dumps(dict(note='Functional manual controls, mixed reused and new fixtures; not independent headline accuracy. All errors retained.',results=results),ensure_ascii=False,indent=2),encoding='utf-8')
  print(i+1,len(rows),kind,'label',row['label'],'predicted',predicted,flush=True)
if __name__=='__main__':main()
