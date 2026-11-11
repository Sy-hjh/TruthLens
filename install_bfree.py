import bootstrap,hashlib,json,zipfile
from range_stream import RangeStream
ROOT=bootstrap.ROOT

def main():
 p=ROOT/'models/bfree';p.mkdir(exist_ok=True);url='https://www.grip.unina.it/download/prog/B-Free/weights/BFREE_dino2reg4.zip';size=321653488;temp=p/'weights.zip.part';offset=temp.stat().st_size if temp.exists() else 0
 with RangeStream(url,size,workers=8,start=offset) as stream,temp.open('ab') as out:
  while chunk:=stream.read(4*1024*1024):out.write(chunk);print(out.tell(),'/',size,flush=True)
 if hashlib.md5(temp.read_bytes()).hexdigest()!='f3f53fa647848b16cf81c913f148a198':raise RuntimeError('Author MD5 mismatch')
 with zipfile.ZipFile(temp) as archive:
  for n in archive.namelist():
   if n.endswith(('config.yaml','model_epoch_best.pth')):
    dest=p/n.split('/')[-1];dest.write_bytes(archive.read(n));print(dest.name,dest.stat().st_size)
 (p/'source.json').write_text(json.dumps(dict(repo='grip-unina/B-Free',url=url,author_md5='f3f53fa647848b16cf81c913f148a198',license='Nonprofit research; preserve author notices',sha256=hashlib.sha256((p/'model_epoch_best.pth').read_bytes()).hexdigest()),indent=2))
if __name__=='__main__':main()
