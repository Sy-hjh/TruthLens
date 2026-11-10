"""Stream a bounded public sample; never extract archive paths to disk."""
import bootstrap
import requests,tarfile,json,hashlib,argparse,shutil
from PIL import Image
root=bootstrap.ROOT/'data/recent2026'
def main():
    p=argparse.ArgumentParser();p.add_argument('--count',type=int,default=20);a=p.parse_args()
    root.mkdir(parents=True,exist_ok=True)
    repo='pthan12/AIGenImages2026'
    r=requests.get('https://huggingface.co/api/datasets/'+repo,timeout=30);r.raise_for_status();meta=r.json();rev=meta['sha']
    r=requests.get(f'https://huggingface.co/datasets/{repo}/raw/{rev}/README.md',timeout=30);r.raise_for_status();(root/'README-source.md').write_text(r.text,encoding='utf-8')
    rows=[]
    from range_stream import RangeStream
    with RangeStream(f'https://huggingface.co/datasets/{repo}/resolve/{rev}/aigenimages2026.tar.gz',11138511098) as response:
        with tarfile.open(fileobj=response,mode='r|gz') as archive:
            for member in archive:
                if not member.isfile() or not member.name.lower().endswith(('.jpg','.jpeg','.png','.webp')):continue
                if member.size>30_000_000:continue
                if shutil.disk_usage(root).free<50*1024**3:raise RuntimeError('保留50GiB系统空间，停止下载')
                stream=archive.extractfile(member);data=stream.read();digest=hashlib.sha256(data).hexdigest();path=root/(digest+'.img')
                path.write_bytes(data)
                with Image.open(path) as im:im.verify()
                rows.append(dict(path=path.relative_to(bootstrap.ROOT).as_posix(),label=1,split='test',group=member.name,sha256=digest,archive_name=member.name))
                (root/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
                print(len(rows),member.name,len(data),flush=True)
                if len(rows)>=a.count:break
    (root/'source.json').write_text(json.dumps(dict(repo=repo,revision=rev,license='cc-by-4.0',archive_bytes=11138511098,full_archive_downloaded=False,sampled_bytes=sum((bootstrap.ROOT/r['path']).stat().st_size for r in rows),count=len(rows),selection='first image entries, convenience sample; AI only, cannot estimate real false positive rate; no independent-generator guarantee'),indent=2),encoding='utf-8')
if __name__=='__main__':main()
