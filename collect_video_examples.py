"""Author-published demo clips only; does not access the gated DeepSpeak dataset."""
import bootstrap,json,re,hashlib
from collect_domain_cases import get
from pathlib import Path
ROOT=bootstrap.ROOT
def main():
    folder=ROOT/'data/public-video-examples';folder.mkdir(exist_ok=True)
    page='https://huggingface.co/datasets/faridlab/deepspeak_v1'
    text=get(page).text;urls=sorted(set(re.findall(r'https[^<> ]+mp4',text)))
    if not urls:raise RuntimeError('Official sample URLs unavailable')
    rows=[]
    for url in urls:
        if not url.startswith('https://data.matsworld.io/ucbresearch/example-'):continue
        path=folder/Path(url).name
        if not path.exists():path.write_bytes(get(url).content)
        rows.append(dict(path=path.relative_to(ROOT).as_posix(),url=url,label='fake' if 'example-fake-' in url else 'real',group=Path(url).stem,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),purpose='small public presentation-example diagnostic, not representative independent accuracy; do not redistribute as licensed full dataset'))
        print(path.name,path.stat().st_size,flush=True)
    (folder/'manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    (folder/'SOURCE.md').write_text('Source: '+page+'\nOnly public Samples links. Main dataset is gated and requires license; not accessed. These demo clips are diagnostic only, no new training and no redistribution in contest archive. Fake-face label does not imply fake voice.\n',encoding='utf-8')
if __name__=='__main__':main()
