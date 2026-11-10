"""Explicit, versioned product-domain inference, enabled only after release checks."""
import json,hashlib
from bootstrap import ROOT
def available():
    path=ROOT/'models/active-domain.json'
    if not path.exists():return False
    try:
        info=json.loads(path.read_text());return all((ROOT/info[k]).is_file() for k in ('weights','head')) and info.get('approved') is True
    except (OSError,ValueError,KeyError):return False
def predict(image):
    if not available():raise RuntimeError('商品场景模型尚未通过发布检查')
    import torch
    from check_recent_model import load
    from domain_model import views,probability,make_head
    from .detector import lock
    info=json.loads((ROOT/'models/active-domain.json').read_text())
    with lock:
        weights=ROOT/info['weights'];head_path=ROOT/info['head']
        if hashlib.sha256(head_path.read_bytes()).hexdigest()!=info['head_sha256']:raise RuntimeError('场景模型文件校验失败')
        if hashlib.sha256(weights.read_bytes()).hexdigest()!=info['weights_sha256']:raise RuntimeError('图像编码器文件校验失败')
        network=load(weights);device=next(network.parameters()).device;head=make_head(info.get('head_type','linear')).to(device)
        head.load_state_dict(torch.load(head_path,weights_only=True,map_location=device));head.eval()
        with torch.inference_mode():
            batch=views(image).to(device);features=network.forward_head(network.forward_features(batch),pre_logits=True).unsqueeze(0);score=probability(head,features).item()
        del network,head
        if device.type=='cuda':torch.cuda.empty_cache()
    return dict(status='completed',score=score,source=dict(repo='亲安商品场景分类头 / Community Forensics冻结编码器',version=info['version']),note='商品场景整图及四个局部视角辅助核验；模型分数不是真伪或诈骗概率，不能证明商品实际损坏。')
