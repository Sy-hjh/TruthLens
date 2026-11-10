"""Resumable compressed/local-view head training, with frozen encoder."""
import bootstrap,json,hashlib,argparse,signal
from pathlib import Path
import torch
from PIL import Image
from check_recent_model import load,statistics
from domain_model import views,aggregate,make_head
from checkpoint_io import save_checkpoint,load_latest,acquire_training_lock
ROOT=bootstrap.ROOT
def main():
    if (ROOT/'runtime/STOP_OPTIMIZATION').exists():print('已请求停止优化');return
    p=argparse.ArgumentParser();p.add_argument('--epochs',type=int,default=60);p.add_argument('--head',choices=['linear','mlp'],default='linear');p.add_argument('--output',default='models/domain-v1');a=p.parse_args();torch.manual_seed(42)
    manifest=ROOT/'data/domain-fit/manifest.json';rows=json.loads(manifest.read_text(encoding='utf-8'))
    external=json.loads((ROOT/'data/domain-cases/manifest.json').read_text(encoding='utf-8'))
    # Exclude complete review groups with byte-identical external/validation
    # content, rather than silently letting repeated marketplace photos leak.
    external_hashes={r['sha256'] for r in external};val_hashes={r['sha256'] for r in rows if r['split']=='val'}
    excluded_groups={r['group'] for r in rows if r['sha256'] in external_hashes or (r['split']=='train' and r['sha256'] in val_hashes)}
    clean=[];seen=set();excluded=[]
    for row in rows:
        if row['group'] in excluded_groups or row['sha256'] in seen:
            excluded.append(row);continue
        seen.add(row['sha256']);clean.append(row)
    rows=clean
    protocol=dict(purpose='new product-domain training; external diagnostic cases excluded',counts={s:sum(r['split']==s for r in rows) for s in ('train','val')},categories={s:sorted(set(r['category'] for r in rows if r['split']==s)) for s in ('train','val')},encoder='frozen Community Forensics ViT',head='linear multiple-instance classifier',views='whole image plus four local views',qualities=[None,60,85],selection='best worst-quality validation balanced accuracy, fixed threshold0.5',excluded_rows=len(excluded))
    (ROOT/'data/domain-fit/training-protocol.json').write_text(json.dumps(protocol,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest=ROOT/'data/domain-fit/training-manifest.json';manifest.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (ROOT/'reports/domain-data-exclusions.json').write_text(json.dumps(excluded,ensure_ascii=False,indent=2),encoding='utf-8')
    assert not {r['sha256'] for r in rows}&external_hashes,'External sample overlap'
    assert not {r['category'] for r in rows if r['split']=='train'}&{r['category'] for r in rows if r['split']=='val'}
    assert not {r['sha256'] for r in rows if r['split']=='train'}&{r['sha256'] for r in rows if r['split']=='val'},'Duplicate content across train/val'
    initial=(ROOT/'models/balanced-v1/best/model.safetensors').read_bytes();base_hash=hashlib.sha256(initial).hexdigest()
    weights=ROOT/'models/releases'/base_hash/'model.safetensors';weights.parent.mkdir(parents=True,exist_ok=True)
    if not weights.exists():weights.write_bytes(initial)
    identity=hashlib.sha256(manifest.read_bytes()+base_hash.encode()+b'global-local-jpeg60-85-v1'+a.head.encode()).hexdigest();folder=ROOT/a.output;folder.mkdir(exist_ok=True);training_lock=acquire_training_lock(folder)
    cache=ROOT/'runtime/domain-features'/(base_hash+'-views-v1');cache.mkdir(parents=True,exist_ok=True)
    network=load(weights);device=next(network.parameters()).device
    for parameter in network.parameters():parameter.requires_grad=False
    features=[];labels=[];splits=[];groups=[]
    for i,row in enumerate(rows):
        key=cache/(row['sha256']+'.pt')
        if key.exists():value=torch.load(key,weights_only=True)
        else:
            with Image.open(ROOT/row['path']) as im:
                batch=torch.cat([views(im,q) for q in (None,60,85)]).to(device)
            with torch.inference_mode():value=network.forward_head(network.forward_features(batch),pre_logits=True).reshape(3,5,-1).cpu()
            temporary=key.with_suffix('.tmp');torch.save(value,temporary);temporary.replace(key)
        features.append(value);labels.extend([row['label']]*3);splits.extend([row['split']]*3);groups.extend([row['group']]*3)
        if i%20==0:print('提取冻结特征',i+1,'/',len(rows),flush=True)
    x=torch.cat(features).to(device);y=torch.tensor(labels,dtype=torch.float32,device=device)
    head=make_head(a.head).to(device)
    if a.head=='linear':head.load_state_dict(network.head.state_dict())
    del network
    optimizer=torch.optim.AdamW(head.parameters(),lr=.0003,weight_decay=.01)
    train=torch.tensor([i for i,s in enumerate(splits) if s=='train'],device=device);val=torch.tensor([i for i,s in enumerate(splits) if s=='val'],device=device)
    counts=torch.bincount(y[train].long());sample_weights=torch.tensor([len(train)/(2*int(c)) for c in counts],device=device)
    epoch=cursor=step=0;best=-1.;stale=0
    saved=load_latest(folder/'last.pt')
    if saved:
        assert saved['manifest']==identity
        head.load_state_dict(saved['head']);optimizer.load_state_dict(saved['optimizer']);epoch,cursor,step,best,stale=(saved[k] for k in ('epoch','cursor','step','best','stale'))
        if 'rng' in saved:torch.set_rng_state(saved['rng'])
        if device.type=='cuda' and 'cuda_rng' in saved:torch.cuda.set_rng_state(saved['cuda_rng'])
    stopped=False
    def stop(*_):
        nonlocal stopped
        stopped=True
    signal.signal(signal.SIGINT,stop)
    def save():save_checkpoint(dict(head=head.state_dict(),optimizer=optimizer.state_dict(),epoch=epoch,cursor=cursor,step=step,best=best,stale=stale,manifest=identity,base='domain-mil-v1',batch_size=64,rng=torch.get_rng_state(),**({'cuda_rng':torch.cuda.get_rng_state()} if device.type=='cuda' else {})),folder/'last.pt')
    while epoch<a.epochs and not stopped:
        if (ROOT/'runtime/STOP_OPTIMIZATION').exists():break
        order=train[torch.randperm(len(train),generator=torch.Generator().manual_seed(42+epoch)).to(device)]
        head.train()
        while cursor<len(order) and not stopped:
            ids=order[cursor:cursor+64];optimizer.zero_grad();logits=aggregate(head(x[ids]).squeeze(-1));loss=torch.nn.functional.binary_cross_entropy_with_logits(logits,y[ids],weight=sample_weights[y[ids].long()])
            if a.head=='mlp':
                pairs=(ids//3).unsqueeze(1)*3+torch.arange(3,device=device)
                probabilities=aggregate(head(x[pairs]).squeeze(-1).reshape(-1,5)).sigmoid().reshape(-1,3)
                loss=loss+probabilities.var(dim=1,unbiased=False).mean()
            loss.backward();optimizer.step();cursor+=len(ids);step+=1;save()
        if stopped:break
        with torch.inference_mode():
            head.eval()
            prediction=(aggregate(head(x[val]).squeeze(-1)).sigmoid()>=.5).long();truth=y[val].long()
            rates=[float((prediction[truth==c]==c).float().mean()) for c in (0,1)];balanced=sum(rates)/2
        variants=[]
        for q in range(3):
            mask=(val%3)==q;vp=prediction[mask];vy=truth[mask]
            qr=[float((vp[vy==c]==c).float().mean()) for c in (0,1)]
            variants.append(dict(quality=[None,60,85][q],balanced_accuracy=sum(qr)/2,real_fpr=1-qr[0],ai_fnr=1-qr[1]))
        score=min(v['balanced_accuracy'] for v in variants)
        metrics=dict(epoch=epoch+1,balanced_accuracy=balanced,worst_quality_balanced_accuracy=score,real_fpr=1-rates[0],ai_fnr=1-rates[1],variants=variants);print(metrics,flush=True)
        if score>best+1e-6:
            best=score;stale=0;head_path=save_checkpoint(head.state_dict(),folder/'best-head.pt');(folder/'selection.json').write_text(json.dumps(dict(**metrics,head_type=a.head,head_file=head_path.relative_to(ROOT).as_posix(),manifest=identity,base_weights_sha256=base_hash,base_weights_relative=weights.relative_to(ROOT).as_posix(),recipe='global-local-jpeg60-85-v1'),indent=2),encoding='utf-8')
        else:stale+=1
        with (folder/'history.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(metrics)+'\n')
        epoch+=1;cursor=0;save()
        if stale>=10:break
    save();print('场景训练已保存',folder,flush=True)
if __name__=='__main__':main()
