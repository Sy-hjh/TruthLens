"""Supplementary CASIA-labelled traditional-edit examples, not native-resolution benchmarks."""
import bootstrap,json,hashlib,io
from pathlib import Path
from collect_domain_cases import get
from PIL import Image
import requests
ROOT=bootstrap.ROOT
def main():
    repo='KhangTruong/Tampered-Images-Combined-Dataset-2';folder=ROOT/'data/ps-examples';folder.mkdir(exist_ok=True)
    params={'dataset':repo,'config':'default','split':'cross_test','where':'"dataset" = \'CASIA2\'','offset':0,'length':30}
    response=requests.get('https://datasets-server.huggingface.co/filter',params=params,timeout=90);response.raise_for_status();d=response.json()
    rows=[]
    for item in d['rows']:
        row=item['row'];data=get(row['image']['src']).content
        with Image.open(io.BytesIO(data)) as im:im.verify()
        digest=hashlib.sha256(data).hexdigest();path=folder/(digest+'.jpg');path.write_bytes(data)
        rows.append(dict(path=path.relative_to(ROOT).as_posix(),label=row['label'],kind='traditional-edit-supplement',dataset=row['dataset'],method=row['method'],group=row['id'],sha256=digest,trainable=False,note='Combined-dataset cached viewer export; resized/re-encoded. Demonstration only, excluded from native-image forensic accuracy. Source labels inherited.'))
    if not rows:raise RuntimeError('No CASIA2 rows returned; do not invent samples')
    meta=get('https://huggingface.co/api/datasets/'+repo).json()
    (folder/'source-readme.md').write_text(get(f'https://huggingface.co/datasets/{repo}/raw/{meta["sha"]}/README.md').text,encoding='utf-8')
    (folder/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (folder/'source.json').write_text(json.dumps(dict(repo=repo,revision=meta['sha'],license=meta.get('cardData',{}).get('license'),count=len(rows),purpose='supplementary traditional-P examples; viewer re-encoding prevents using these as native-forensics benchmark'),indent=2),encoding='utf-8')
    print('Traditional-edit supplementary examples:',len(rows))
if __name__=='__main__':main()
