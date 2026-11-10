"""Download a small labelled pilot, with provenance and resumable per-file cache."""
import bootstrap
import requests,json,base64,hashlib,time,zipfile,io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

root=bootstrap.ROOT/'data/recent'; root.mkdir(parents=True,exist_ok=True)
session=requests.Session()
def get(url,**kwargs):
    for attempt in range(6):
        try:
            r=session.get(url,timeout=90,**kwargs);r.raise_for_status();return r
        except requests.RequestException:
            if attempt==5:raise
            time.sleep(2)

def main():
    repo='OwensLab/CommunityForensics-Small'
    meta=get('https://huggingface.co/api/datasets/'+repo).json()
    (root/'DATASET_README.md').write_text(get(f'https://huggingface.co/datasets/{repo}/raw/{meta["sha"]}/README.md').text,encoding='utf-8')
    rows=[]
    archive=get('https://github.com/ultralytics/assets/releases/download/v0.0.0/coco8.zip').content
    (root/'coco8.zip').write_bytes(archive)
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for name in z.namelist():
            if '/images/' not in name or not name.endswith('.jpg'):continue
            data=z.read(name);digest=hashlib.sha256(data).hexdigest();path=root/(digest+'.jpg');path.write_bytes(data)
            rows.append(dict(path=path.relative_to(bootstrap.ROOT).as_posix(),label=0,split='val' if '/val/' in name else 'train',group='COCO8',source_row=name,sha256=digest))
    for label in (1,):
        params=dict(dataset=repo,config='default',split='train',offset=0,length=10)
        result=get('https://datasets-server.huggingface.co/rows',params=params).json()
        for item in result['rows']:
            row=item['row']
            if int(row['label'])!=label:raise ValueError('Label mismatch')
            if row.get('nsfw_flag'):continue
            data=base64.b64decode(row['image_data']); digest=hashlib.sha256(data).hexdigest()
            path=root/(digest+'.png')
            if not path.exists():path.write_bytes(data)
            with Image.open(path) as im: im.verify()
            rows.append(dict(path=path.relative_to(bootstrap.ROOT).as_posix(),label=label,split='val' if len([r for r in rows if r['label']==label])%5==0 else 'train',group=row.get('model_name') or row.get('real_source'),source_row=item['row_idx'],sha256=digest))
        print('Downloaded label',label,'count',sum(r['label']==label for r in rows),flush=True)
    (root/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'source.json').write_text(json.dumps(dict(repo=repo,revision=meta['sha'],license='cc-by-nc-sa-4.0',real_source='https://github.com/ultralytics/assets/releases/download/v0.0.0/coco8.zip',real_archive_sha256=hashlib.sha256(archive).hexdigest(),purpose='tiny pipeline pilot ONLY; COCO photos vs generated images has source bias; NOT accuracy evidence; model/source groups may overlap',count=len(rows)),indent=2),encoding='utf-8')

if __name__=='__main__':main()
