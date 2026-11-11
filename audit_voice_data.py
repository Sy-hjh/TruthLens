"""Reject byte overlap across splits and contradictory labels before head training."""
import bootstrap,json,collections,hashlib
def audit():
 root=bootstrap.ROOT;path=root/'data/clone-bench/manifest.json'
 if path.exists():rows=json.loads(path.read_text(encoding='utf-8'))
 else:
  planned=json.loads((path.parent/'planned.json').read_text(encoding='utf-8'))['rows'];rows=[]
  for row in planned:
   file=path.parent/'audio'/(hashlib.sha256(row['remote'].encode()).hexdigest()+'.wav')
   if file.exists():digest=hashlib.sha256(file.read_bytes()).hexdigest()
   elif row['split']=='test' and row.get('published_sha256'):digest=row['published_sha256']
   else:raise RuntimeError('Training/validation download incomplete; cannot train yet')
   if row.get('published_sha256') and digest!=row['published_sha256']:raise RuntimeError('Published sample hash mismatch')
   rows.append(dict(row,path=file.relative_to(root).as_posix(),sha256=digest,download_verified=file.exists()))
 groups=collections.defaultdict(list)
 for r in rows:groups[r['sha256']].append(r)
 bad={h for h,items in groups.items() if len({r['split'] for r in items})>1 or len({r['label'] for r in items})>1}
 pairs={r['pair'] for r in rows if r['sha256'] in bad};kept=[r for r in rows if r['pair'] not in pairs]
 (path.parent/'manifest-audited.json').write_text(json.dumps(kept,ensure_ascii=False,indent=2),encoding='utf-8')
 report=dict(raw_count=len(rows),retained_count=len(kept),excluded_pairs=sorted(pairs),conflicting_or_cross_split_hashes=len(bad),raw_manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None,pending_test_downloads=sum(r.get('download_verified') is False for r in rows),speaker_counts={s:len({r['speaker'] for r in kept if r['split']==s}) for s in ('train','val','test')},counts={s:{str(label):sum(r['split']==s and r['label']==label for r in kept) for label in (0,1)} for s in ('train','val','test')})
 (root/'reports/voice-data-audit.json').write_text(json.dumps(report,indent=2));print(report,flush=True)
if __name__=='__main__':audit()
