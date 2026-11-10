"""Small paired video-call diagnostic from the public RTFS source, not training."""
import bootstrap,json,csv,io,hashlib
from pathlib import Path
from collect_domain_cases import get
from backend.media import sample_video
from backend.detector import classify
ROOT=bootstrap.ROOT
def main():
    repo='kontur-ai/rtfs-10k';folder=ROOT/'data/video-diagnostic';folder.mkdir(exist_ok=True)
    meta=get('https://huggingface.co/api/datasets/'+repo).json();rev=meta['sha'];base=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/'
    (folder/'README-source.md').write_text(get(base+'README.md').text,encoding='utf-8')
    tables={g:list(csv.DictReader(io.StringIO(get(base+g+'.csv').text))) for g in ('inswapper','uniface')}
    by_video={g:{} for g in tables}
    for generator,rows in tables.items():
        for row in rows:
            if row['success'].lower()=='true':by_video[generator].setdefault(row['video'],row)
    selected=[];seen=set();genders={'man':0,'woman':0}
    for video in sorted(set(by_video['inswapper'])&set(by_video['uniface'])):
        name=Path(video).stem;identity,start,end=name.rsplit('_',2)
        tags=[x.strip() for x in by_video['inswapper'][video]['video_tags'].split(';')]
        gender='woman' if 'woman' in tags else 'man' if 'man' in tags else None
        if not gender or genders[gender]>=3 or identity in seen or int(end)-int(start)>12:continue
        genders[gender]+=1;seen.add(identity);selected.append(video)
        if len(selected)==6:break
    if len(selected)!=6:raise RuntimeError('Insufficient matched short clips')
    planned=[]
    for video in selected:
        planned.append(dict(remote='original_videos/'+video,label=0,group=video,generator='none'))
        for generator in tables:planned.append(dict(remote=generator+'/'+by_video[generator][video]['filename'],label=1,group=video,generator=generator))
    results=[]
    for row in planned:
        path=folder/Path(row['remote']).name
        if not path.exists():path.write_bytes(get(base+row['remote']).content)
        duration,frames=sample_video(path,16);images=[im for _,im in frames]
        while len(images)<16:images.append(images[-1])
        output=classify('video',images);results.append(dict(row,path=path.relative_to(ROOT).as_posix(),duration=duration,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),score=output['score'],predicted=int(output['score']>=.5)))
        print(len(results),'/',len(planned),row['generator'],output['score'],flush=True)
        (ROOT/'reports/video-diagnostic-progress.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    from check_recent_model import statistics
    report=dict(repo=repo,revision=rev,license=meta.get('cardData',{}).get('license'),metrics=statistics(results),results=results,note='6 paired originals and12 face swaps, selected short clips with source success=True; small convenience diagnostic, not representative elderly/current generators accuracy. Voice labels not inferred from face-swap label. Source authors report CC YouTube origins, no identity claim.')
    (ROOT/'reports/video-diagnostic.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(report['metrics'])
if __name__=='__main__':main()
