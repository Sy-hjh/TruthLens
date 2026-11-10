"""Audit the downloaded balanced pilot before manual training."""
import bootstrap,json,hashlib,shutil
from collections import Counter
from pathlib import Path
def main():
    root=bootstrap.ROOT
    rows=json.loads((root/'data/balanced-v1/manifest.json').read_text(encoding='utf-8'))
    assert len(rows)==4000
    counts=Counter((r['split'],r['label']) for r in rows)
    assert sum(r['label']==0 for r in rows)==sum(r['label']==1 for r in rows)==2000
    unique=set();size=0;groups={s:set() for s in ('train','val','test')}
    for r in rows:
        path=(root/r['path']).resolve();assert path.is_relative_to(root)
        data=path.read_bytes();digest=hashlib.sha256(data).hexdigest();assert digest==r['sha256'];assert digest not in unique;unique.add(digest);size+=len(data)
        if r['label']==1:groups[r['split']].add(r['group'])
    assert not (groups['train']&groups['val'] or groups['train']&groups['test'] or groups['val']&groups['test'])
    for split in ('train','val','test'):assert counts[split,0]==counts[split,1]>0
    result=dict(images=len(rows),image_bytes=size,free_bytes=shutil.disk_usage(root).free,counts={s:{'real':counts[s,0],'fake':counts[s,1]} for s in groups},generator_groups={s:sorted(g) for s,g in groups.items()},checks='all file SHA256 verified; no duplicate content; fake generator groups locally disjoint; both classes balanced per split',limitation='Not independent of all base-model pretraining; COCO source bias remains; no accuracy claim')
    (root/'reports/balanced-data-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
