"""Reassemble split LFS files and verify every distributed model artifact."""
import hashlib,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def main():
 rows=json.loads((ROOT/'docs/all-model-files.json').read_text(encoding='utf-8'))
 for row in rows:
  target=ROOT/row['path']
  if row['parts'] and not target.exists():
   temporary=target.with_suffix(target.suffix+'.assembling')
   try:
    digest=hashlib.sha256();count=0
    with temporary.open('wb') as output:
     for name in row['parts']:
      with (ROOT/name).open('rb') as source:
       for block in iter(lambda:source.read(8*1024**2),b''):
        output.write(block);digest.update(block);count+=len(block)
    if count!=row['bytes'] or digest.hexdigest()!=row['sha256']:raise ValueError('Split file verification failed: '+row['path'])
    os.replace(temporary,target)
   finally:
    temporary.unlink(missing_ok=True)
  digest=hashlib.sha256()
  with target.open('rb') as source:
   for block in iter(lambda:source.read(8*1024**2),b''):digest.update(block)
  if target.stat().st_size!=row['bytes'] or digest.hexdigest()!=row['sha256']:raise ValueError('Missing LFS content or checksum mismatch: '+row['path'])
  print('OK',row['path'],flush=True)
 print('All model artifacts verified. Native OCR/DAF dependencies remain separate; see docs/ENVIRONMENT.md.')
if __name__=='__main__':main()
