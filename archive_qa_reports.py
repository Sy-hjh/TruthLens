"""Reversibly hide ONLY byte-matched public QA fixtures / explicitly marked demos."""
import bootstrap,json,hashlib,argparse
from bootstrap import ROOT
from backend import storage
def main():
 p=argparse.ArgumentParser();p.add_argument('--restore',action='store_true');a=p.parse_args();log=ROOT/'runtime/archived-qa-reports.json'
 if a.restore:
  for item in json.loads(log.read_text(encoding='utf-8')):
   r=storage.get(item['id'])
   if r:r.pop('internal_only',None);storage.update(r)
  print('Restored archived QA visibility');return
 files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'演示素材_八个').glob('*') if p.is_file()}
 files.update({'test.mp4':hashlib.sha256(b'public-test').hexdigest()})
 known_hashes={name:{digest} for name,digest in files.items()}
 # Earlier fixture revisions: match exact bytes from the recorded local source.
 for manifest in (ROOT/'reports').glob('eight-demo-verified*.json'):
  records=json.loads(manifest.read_text(encoding='utf-8'))
  if not isinstance(records,list):continue
  for item in records:
   source=(ROOT/item.get('source','')).resolve()
   if source.is_relative_to(ROOT.resolve()) and source.is_file() and item.get('file'):
    known_hashes.setdefault(item['file'],set()).add(hashlib.sha256(source.read_bytes()).hexdigest())
 archived=[]
 with storage.connection() as db:rows=[json.loads(x[0]) for x in db.execute('SELECT body FROM cases')]
 for r in rows:
  explicit=r.get('context','').startswith(('公开研究数据对照','明确标注的通用合成语音反诈模拟','__truthlens_qa__'))
  matched=r.get('sha256') in known_hashes.get(r.get('filename'),set())
  if (explicit or matched) and not r.get('internal_only'):
   r['internal_only']=True;storage.update(r);archived.append(dict(id=r['id'],reason='explicit_demo' if explicit else 'exact_public_fixture_hash'))
 previous=json.loads(log.read_text(encoding='utf-8')) if log.exists() else []
 log.write_text(json.dumps(previous+archived,indent=2),encoding='utf-8');print('Archived QA records:',len(archived),'Original results and media source files unchanged; reversible.')
if __name__=='__main__':main()
