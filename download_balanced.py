"""Capacity-limited first substantial pilot. Originals retained, no made-up labels."""
import bootstrap
import argparse,json,hashlib,io,zipfile,random,time,shutil,subprocess,sys,re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import requests
from PIL import Image

ROOT=bootstrap.ROOT
DEST=ROOT/'data/balanced-v1'
def fetch(url):
    for attempt in range(6):
        try:
            r=requests.get(url,timeout=(30,90));r.raise_for_status();return r.content
        except requests.RequestException:
            if attempt==5:raise
            time.sleep(2)
def main():
    p=argparse.ArgumentParser();p.add_argument('--per-class',type=int,default=2000);p.add_argument('--reuse-fake',action='store_true');a=p.parse_args()
    if shutil.disk_usage(ROOT).free<60*1024**3:raise RuntimeError('Keep at least60GiB free before starting')
    DEST.mkdir(parents=True,exist_ok=True)
    # Stream only the required prefix. Per-image cache survives interruptions;
    # gzip restarts must re-read the prefix, not a byte-range resume.
    if not a.reuse_fake:subprocess.run([sys.executable,str(ROOT/'download_2026_pilot.py'),'--count',str(a.per_class)],check=True)
    fake=json.loads((ROOT/'data/recent2026/manifest.json').read_text(encoding='utf-8'))
    archive=fetch('https://s3.amazonaws.com/images.cocodataset.org/annotations/image_info_test2017.zip')
    (DEST/'coco-image-info.zip').write_bytes(archive)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        name=next(n for n in z.namelist() if n.endswith('image_info_test2017.json'))
        info=json.loads(z.read(name))
    images=sorted(info['images'],key=lambda r:r['id']);random.Random(42).shuffle(images);images=images[:a.per_class]
    folder=DEST/'real';folder.mkdir(exist_ok=True)
    def one(item):
        if shutil.disk_usage(ROOT).free<50*1024**3:raise RuntimeError('Stopped: preserve50GiB system space')
        name=Path(item['file_name']).name;path=folder/name
        if not path.exists():
            data=fetch('https://s3.amazonaws.com/images.cocodataset.org/test2017/'+name)
            with Image.open(io.BytesIO(data)) as im:im.verify()
            temp=path.with_suffix('.part');temp.write_bytes(data);temp.replace(path)
        digest=hashlib.sha256(path.read_bytes()).hexdigest()
        return dict(path=path.relative_to(ROOT).as_posix(),label=0,sha256=digest,group='COCO-test2017-'+str(item['id']),source_id=item['id'],license_id=item.get('license'))
    real=[]
    with ThreadPoolExecutor(max_workers=12) as pool:
        for row in pool.map(one,images):
            real.append(row)
            if len(real)%100==0:print('Real photos:',len(real),'/',len(images),flush=True)
    # Split fake by generator, rather than placing same generator in all splits.
    for row in fake:
        name=Path(row['archive_name']).name
        group=re.sub(r'_[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}_\d+\.[^.]+$','',name)
        if group==name:group=re.sub(r'_\d+\.[^.]+$','',name)
        if name.startswith('Firefly_'):group='Adobe-Firefly'
        row['group']=group
    groups=sorted(set(r['group'] for r in fake));random.Random(42).shuffle(groups)
    if not 3<=len(groups)<=40:raise RuntimeError('Generator names require audit before splitting; do not train automatically')
    n=max(1,len(groups)//5);assignment={g:('test' if i<n else 'val' if i<2*n else 'train') for i,g in enumerate(groups)}
    for r in fake:r['split']=assignment[r['group']]
    counts={s:sum(r['split']==s for r in fake) for s in ('train','val','test')}
    cursor=0
    for split,count in counts.items():
        for r in real[cursor:cursor+count]:r['split']=split
        cursor+=count
    rows=fake+real
    if len(fake)!=a.per_class or len(real)!=a.per_class:raise RuntimeError('Sample count mismatch')
    if len({r['sha256'] for r in rows})!=len(rows):raise RuntimeError('Duplicate images found; split must be audited')
    (DEST/'source.json').write_text(json.dumps(dict(fake_source=json.loads((ROOT/'data/recent2026/source.json').read_text()),real_source='COCO test2017 official S3 bucket',metadata_sha256=hashlib.sha256(archive).hexdigest(),licenses=info.get('licenses'),counts=counts,fake_generator_assignment=assignment,note='Convenience prefix; fake generators isolated locally; COCO real-source bias remains. This is image generation, not video/audio/P-edit training.'),ensure_ascii=False,indent=2),encoding='utf-8')
    temp=DEST/'manifest.tmp';temp.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(DEST/'manifest.json')
    print('READY',len(rows),counts,flush=True)
if __name__=='__main__':main()
