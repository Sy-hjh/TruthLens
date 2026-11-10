"""News illustrations are unverified cases, not ground-truth training labels."""
import bootstrap,json,hashlib,io
from pathlib import Path
from collect_domain_cases import get
from PIL import Image
ROOT=bootstrap.ROOT;folder=ROOT/'data/news-cases'
def main():
    folder.mkdir(exist_ok=True)
    page='https://m.voc.com.cn/xhn/news/202508/30206702.html'
    assets=[('衣服污渍','cf6300e740de3fc01537621b687ea21517da88841755087384.jpg'),('杯子裂纹一','1372b4cb4af414a3e69c2d6c27d1e949b94f8d121755087385.jpg'),('杯子裂纹二','9df2991edae1c8cd9b830ad90245b1ed2ce2025b1755087385.jpg'),('自行车座','02aecdf33809148ec9c2cb61e219e975e64d4db01755087385.jpg')]
    rows=[]
    for title,name in assets:
        url='https://img2.voc.com.cn/9/2025/08/13/'+name
        data=get(url).content
        with Image.open(io.BytesIO(data)) as im:im.verify()
        path=folder/name;path.write_bytes(data)
        rows.append(dict(path=path.relative_to(ROOT).as_posix(),title=title,source_page=page,asset_url=url,published='2025-08-13',label=None,label_status='unverified-news-claim',trainable=False,sha256=hashlib.sha256(data).hexdigest(),note='News allegation/illustration only; not independent ground truth; do not identify or accuse individuals. Copyright remains with source.'))
    (folder/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Collected',len(rows),'unverified news examples; excluded from metrics/training')
if __name__=='__main__':main()
