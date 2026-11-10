"""Create a reproducible tiny mixed pilot, not a representative benchmark."""
import bootstrap,json,hashlib
from pathlib import Path
root=bootstrap.ROOT
def main():
    rows=json.loads((root/'data/recent/manifest.json').read_text(encoding='utf-8'))+json.loads((root/'data/recent2026/manifest.json').read_text(encoding='utf-8'))
    result=[]
    for label in (0,1):
        selected=sorted([r for r in rows if r['label']==label],key=lambda r:r['sha256'])
        val_count=2 if label==0 else 4;test_count=2 if label==0 else 4
        for i,r in enumerate(selected):
            r=dict(r);r['split']='test' if i<test_count else 'val' if i<test_count+val_count else 'train';result.append(r)
    dest=root/'data/training';dest.mkdir(exist_ok=True)
    (dest/'manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (dest/'README.txt').write_text('37-image convenience pilot. train25/val6/test6. Source/generator groups overlap. NOT independent domain accuracy. AIGenImages original archive train items locally repartitioned. Never use private user regression images for training.',encoding='utf-8')
    print({s:sum(r['split']==s for r in result) for s in ['train','val','test']})
if __name__=='__main__':main()
