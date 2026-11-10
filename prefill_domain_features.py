"""Use download time to cache frozen features; labels never used here."""
import bootstrap,time,hashlib
from pathlib import Path
import torch
from PIL import Image
from check_recent_model import load
from domain_model import views
ROOT=bootstrap.ROOT
def main():
    raw=(ROOT/'models/balanced-v1/best/model.safetensors').read_bytes();digest=hashlib.sha256(raw).hexdigest();weights=ROOT/'models/releases'/digest/'model.safetensors';weights.parent.mkdir(parents=True,exist_ok=True)
    if not weights.exists():weights.write_bytes(raw)
    network=load(weights);device=next(network.parameters()).device;cache=ROOT/'runtime/domain-features'/(digest+'-views-v1');cache.mkdir(parents=True,exist_ok=True)
    seen=set();count=0
    while True:
        if (ROOT/'runtime/STOP_OPTIMIZATION').exists():return
        for path in sorted((ROOT/'data/domain-fit/images').glob('*.jpg')):
            if path in seen:continue
            try:
                key=cache/(hashlib.sha256(path.read_bytes()).hexdigest()+'.pt')
                if not key.exists():
                    with Image.open(path) as im:batch=torch.cat([views(im,q) for q in (None,60,85)]).to(device)
                    with torch.inference_mode():value=network.forward_head(network.forward_features(batch),pre_logits=True).reshape(3,5,-1).cpu()
                    tmp=key.with_suffix('.tmp');torch.save(value,tmp);tmp.replace(key)
                seen.add(path);count+=1
                if count%20==0:print('已缓存特征',count,flush=True)
            except (OSError,RuntimeError) as error:print('稍后重试',path.name,type(error).__name__,flush=True)
        if (ROOT/'data/domain-fit/manifest.json').exists():break
        time.sleep(5)
    print('特征缓存完成',count,flush=True)
if __name__=='__main__':main()
