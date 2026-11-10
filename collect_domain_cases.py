"""Collect published, source-labelled product cases. Evaluation only, no training."""
import bootstrap,json,hashlib,time,io,argparse,random
from pathlib import Path
from urllib.parse import quote
from concurrent.futures import ThreadPoolExecutor
import requests
from PIL import Image
ROOT=bootstrap.ROOT;DEST=ROOT/'data/domain-cases'
def get(url):
    for attempt in range(6):
        try:
            r=requests.get(url,timeout=(30,90));r.raise_for_status();return r
        except requests.RequestException as error:
            print('Retry',attempt+1,type(error).__name__,url,flush=True)
            if attempt==5:raise
            time.sleep(1+attempt)
def main():
    global DEST
    parser=argparse.ArgumentParser();parser.add_argument('--training',action='store_true');args=parser.parse_args()
    if args.training:DEST=ROOT/'data/domain-fit'
    DEST.mkdir(exist_ok=True)
    repo='TristanYan/FraudBench';meta=get('https://huggingface.co/api/datasets/'+repo).json();rev=meta['sha'];names=[x['rfilename'] for x in meta['siblings']]
    (DEST/'upstream-readme.md').write_text(get(f'https://huggingface.co/datasets/{repo}/raw/{rev}/README.md').text,encoding='utf-8')
    categories=['Home & Kitchen','Electronics','Grocery & Gourmet Food','Clothing, Shoes & Jewelry','Sports & Outdoors','Toys & Games']
    assignment={}
    if args.training:
        categories=sorted(set(n.split('/')[0] for n in names if '/Positive/' in n)-set(categories))
        random.Random(42).shuffle(categories)
        assignment={c:('val' if i<5 else 'train') for i,c in enumerate(categories)}
    limit=3 if args.training else 5
    models=sorted(set(n.split('/')[2] for n in names if '/DeepFake/' in n and n.endswith('.jpg')))
    planned=[];metadata=[]
    for category in categories:
        positive=sorted(n for n in names if n.startswith(category+'/Positive/') and n.endswith('.jpg'))
        selected=[];seen=set()
        for name in positive:
            review=name.split('/')[2]
            if review in seen:continue
            if not all(f'{category}/DeepFake/{m}/{review}/{Path(name).name}' in names for m in models):continue
            selected.append(name);seen.add(review)
            if len(selected)==limit:break
        if len(selected)!=limit:raise ValueError('Insufficient complete cases for '+category)
        for name in selected:
            review=name.split('/')[2];case=category+'/'+review
            planned.append(dict(upstream_path=name,label=0,kind='published-real-undamaged',category=category,group=case,generator='none'))
            for model in models:
                planned.append(dict(upstream_path=f'{category}/DeepFake/{model}/{review}/{Path(name).name}',label=1,kind='published-ai-edited',category=category,group=case,generator=model))
            metadata.append(f'{category}/DeepFake/Metadata/Edit_{review.split("_")[1]}.json')
        negatives=sorted(n for n in names if n.startswith(category+'/Negative/') and n.endswith('.jpg'));seen=set();count=0
        for name in negatives:
            review=name.split('/')[2]
            if review in seen:continue
            seen.add(review);planned.append(dict(upstream_path=name,label=0,kind='published-real-damaged',category=category,group=category+'/negative/'+review,generator='none'));count+=1
            if count==limit:break
    def one(row):
        name=row['upstream_path'];url=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/'+quote(name,safe='/')
        local=DEST/'images'/(hashlib.sha256(name.encode()).hexdigest()+'.jpg');local.parent.mkdir(exist_ok=True)
        if not local.exists():
            data=get(url).content
            with Image.open(io.BytesIO(data)) as im:im.verify()
            local.write_bytes(data)
        return dict(row,path=local.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(local.read_bytes()).hexdigest(),split=assignment.get(row['category'],'external-eval'),source_url=url,label_basis='FraudBench author directory and metadata; not independently verified identity or fraud',source_revision=rev)
    rows=[]
    with ThreadPoolExecutor(max_workers=4) as pool:
        for row in pool.map(one,planned):
            rows.append(row)
            if len(rows)%20==0:print('Collected',len(rows),'/',len(planned),flush=True)
    folder=DEST/'metadata';folder.mkdir(exist_ok=True)
    for name in metadata:
        path=folder/(hashlib.sha256(name.encode()).hexdigest()+'.json')
        if not path.exists():path.write_bytes(get(f'https://huggingface.co/datasets/{repo}/resolve/{rev}/'+quote(name,safe='/')).content)
    source=dict(repo=repo,revision=rev,license=meta.get('cardData',{}).get('license'),purpose=('new product-domain training with category-held-out validation' if args.training else 'external product-domain diagnostic only; do not train on this evaluation set'),models=models,selection=('23 remaining categories; up to three distinct positive and negative review groups per category; five categories held out for validation' if args.training else 'six product categories; first five distinct positive review groups with all generators; first five distinct negative groups'),count=len(rows),bytes=sum((ROOT/r['path']).stat().st_size for r in rows),note='Negative means real damaged review, not fake. AI rows are local edit/generation evidence, not assumed whole-image synthesis. Real-damaged and real-undamaged reviews are not before/after pairs.')
    (DEST/'source.json').write_text(json.dumps(source,ensure_ascii=False,indent=2),encoding='utf-8')
    (DEST/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(source,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
