"""Frozen VideoMAE head adaptation; source-video and generator held-out split."""
import bootstrap,json,csv,io,hashlib,random,signal
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import torch
from transformers import VideoMAEImageProcessor,VideoMAEForVideoClassification
from backend.media import sample_video
from collect_domain_cases import get
from checkpoint_io import save_checkpoint,load_latest,acquire_training_lock
from check_recent_model import statistics
ROOT=bootstrap.ROOT
def main():
    if (ROOT/'runtime/STOP_OPTIMIZATION').exists():print('已请求停止优化');return
    folder=ROOT/'data/video-fit';folder.mkdir(exist_ok=True);manifest=folder/'manifest.json'
    if not manifest.exists():
        repo='kontur-ai/rtfs-10k';meta=get('https://huggingface.co/api/datasets/'+repo).json();rev=meta['sha'];base=f'https://huggingface.co/datasets/{repo}/resolve/{rev}/'
        (folder/'README-source.md').write_text(get(base+'README.md').text,encoding='utf-8')
        tables={g:list(csv.DictReader(io.StringIO(get(base+g+'.csv').text))) for g in ('inswapper','uniface')}
        matched={g:{} for g in tables}
        for g,items in tables.items():
            for row in items:
                if row['success'].lower()=='true':matched[g].setdefault(row['video'],row)
        excluded=set()
        diagnostic=ROOT/'reports/video-diagnostic-progress.json'
        if diagnostic.exists():excluded={Path(r['group']).stem.rsplit('_',2)[0] for r in json.loads(diagnostic.read_text())}
        candidates=[];seen=set(excluded)
        for video in sorted(set(matched['inswapper'])&set(matched['uniface'])):
            identity,start,end=Path(video).stem.rsplit('_',2)
            if identity in seen or int(end)-int(start)>12:continue
            seen.add(identity);candidates.append(video)
        random.Random(42).shuffle(candidates)
        if len(candidates)<150:raise RuntimeError('Not enough distinct short source videos')
        planned=[]
        for i,video in enumerate(candidates[:150]):
            split='train' if i<100 else 'val' if i<125 else 'test';g='uniface' if split=='test' else 'inswapper'
            planned.extend([dict(remote='original_videos/'+video,label=0,group=video,split=split,generator='none'),dict(remote=g+'/'+matched[g][video]['filename'],label=1,group=video,split=split,generator=g)])
        def fetch(row):
            path=folder/Path(row['remote']).name
            if not path.exists():
                data=get(base+row['remote']).content;tmp=path.with_suffix('.part');tmp.write_bytes(data);tmp.replace(path)
            return dict(row,path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        rows=[]
        with ThreadPoolExecutor(max_workers=4) as pool:
            for row in pool.map(fetch,planned):
                rows.append(row)
                if len(rows)%20==0:print('视频下载',len(rows),'/300',flush=True)
        manifest.write_text(json.dumps(rows,indent=2),encoding='utf-8');(folder/'source.json').write_text(json.dumps(dict(repo=repo,revision=rev,license='cc-by-sa-4.0',notes='150 distinct source YouTube IDs, not independently verified actor identities. Train/val inswapper, test uniface. Face labels only; not voice labels.'),indent=2),encoding='utf-8')
    rows=json.loads(manifest.read_text());out=ROOT/'models/video-face-adapt';out.mkdir(exist_ok=True);lock=acquire_training_lock(out);identity=hashlib.sha256(manifest.read_bytes()+b'face-v1').hexdigest()
    processor=VideoMAEImageProcessor.from_pretrained(ROOT/'models/video',local_files_only=True);network=VideoMAEForVideoClassification.from_pretrained(ROOT/'models/video',local_files_only=True).eval();device='cuda' if torch.cuda.is_available() else 'cpu';network=network.to(device)
    cache=ROOT/'runtime/video-features';cache.mkdir(exist_ok=True);features=[];usable=[];rejected=[]
    for i,row in enumerate(rows):
        target=cache/(row['sha256']+'-face-v1.pt')
        if target.exists():feature=torch.load(target,weights_only=True)
        else:
            _,frames=sample_video(ROOT/row['path'],16);images=[im for _,im in frames]
            while len(images)<16:images.append(images[-1])
            from backend.faces import face_views
            try:images,_=face_views(images)
            except ValueError as exc:
                rejected.append(dict(row,reason=str(exc)));continue
            inputs=processor(images,return_tensors='pt').to(device)
            with torch.inference_mode():feature=network.fc_norm(network.videomae(**inputs).last_hidden_state.mean(1)).cpu()
            temporary=target.with_suffix('.tmp');torch.save(feature,temporary);temporary.replace(target)
        features.append(feature);usable.append(row)
        if i%20==0:print('视频特征',i+1,'/300',flush=True)
    (out/'coverage.json').write_text(json.dumps(dict(planned=len(rows),usable=len(usable),rejected=rejected),ensure_ascii=False,indent=2),encoding='utf-8')
    rows=usable
    x=torch.cat(features).to(device);fake=[int(k) for k,v in network.config.id2label.items() if v.lower()=='fake'][0]
    y=torch.tensor([fake if r['label'] else 1-fake for r in rows],device=device);head=network.classifier;del network
    optimizer=torch.optim.AdamW(head.parameters(),lr=.001);epoch=cursor=step=0;best=-1.;stale=0;stopped=False
    saved=load_latest(out/'last.pt')
    if saved:
        assert saved['manifest']==identity
        head.load_state_dict(saved['head']);optimizer.load_state_dict(saved['optimizer']);epoch,cursor,step,best,stale=(saved[k] for k in ('epoch','cursor','step','best','stale'))
    def stop(*_):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGINT,stop)
    def save():save_checkpoint(dict(base='videomae-frozen-head',batch_size=32,manifest=identity,head=head.state_dict(),optimizer=optimizer.state_dict(),epoch=epoch,cursor=cursor,step=step,best=best,stale=stale),out/'last.pt')
    ids={s:torch.tensor([i for i,r in enumerate(rows) if r['split']==s],device=device) for s in ('train','val','test')}
    def evaluate(split):
        indices=ids[split]
        with torch.inference_mode():scores=head(x[indices]).softmax(-1)[:,fake].cpu().tolist()
        return [dict(rows[int(index)],score=score,predicted=int(score>=.5)) for index,score in zip(indices.cpu(),scores)]
    while epoch<100 and not stopped:
        if (ROOT/'runtime/STOP_OPTIMIZATION').exists():stopped=True;break
        order=ids['train'][torch.randperm(len(ids['train']),generator=torch.Generator().manual_seed(epoch+42)).to(device)]
        while cursor<len(order) and not stopped:
            index=order[cursor:cursor+32];optimizer.zero_grad();loss=torch.nn.functional.cross_entropy(head(x[index]),y[index]);loss.backward();optimizer.step();cursor+=len(index);step+=1;save()
        if stopped:break
        metric=statistics(evaluate('val'));print('视频验证',epoch+1,metric,flush=True)
        if metric['balanced_accuracy']>best:
            best=metric['balanced_accuracy'];stale=0;best_path=save_checkpoint(head.state_dict(),out/'best-head.pt')
            (out/'best-path.txt').write_text(str(best_path),encoding='utf-8')
        else:stale+=1
        epoch+=1;cursor=0;save()
        if stale>=15:break
    if not stopped:
        head.load_state_dict(torch.load(Path((out/'best-path.txt').read_text()),map_location=device,weights_only=True));test=evaluate('test');report=dict(metrics=statistics(test),results=test,rejected=rejected,manifest_sha256=identity,note='Planned 25 real and 25 unseen-uniface generator test clips; face abstentions listed separately. Source IDs isolated, actor identities not verified. Small diagnostic, not elderly-domain accuracy.')
        (ROOT/'reports/video-face-adapt-test.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(report['metrics'])
    save()
if __name__=='__main__':main()
