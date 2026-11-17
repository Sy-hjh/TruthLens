"""Explicit, versioned product-domain inference, enabled only after release checks."""
import json,hashlib
from bootstrap import ROOT
def configured_general():
    try:
        return json.loads((ROOT/'models/active-domain.json').read_text(encoding='utf-8')).get('general_image') is True
    except (OSError, ValueError):return False
def _release(general):
    info=json.loads((ROOT/'models/active-domain.json').read_text(encoding='utf-8'))
    if general:
        info.update(info.get('general_head', {}))
    return info
def available(*, general=False):
    try:
        info=_release(general);return all((ROOT/info[k]).is_file() for k in ('weights','head')) and info.get('approved') is True
    except (OSError,ValueError,KeyError):return False
def predict(image, *, general=False):
    if not available(general=general):raise RuntimeError('图片模型尚未通过发布检查')
    import torch
    from check_recent_model import load
    from domain_model import views,probability,make_head
    from .detector import lock
    info=_release(general)
    center_crop=info.get('preprocessing')=='center_crop'
    with lock:
        weights=ROOT/info['weights'];head_path=ROOT/info['head']
        if hashlib.sha256(head_path.read_bytes()).hexdigest()!=info['head_sha256']:raise RuntimeError('场景模型文件校验失败')
        if hashlib.sha256(weights.read_bytes()).hexdigest()!=info['weights_sha256']:raise RuntimeError('图像编码器文件校验失败')
        network=load(weights);device=next(network.parameters()).device;head=make_head(info.get('head_type','linear')).to(device)
        head.load_state_dict(torch.load(head_path,weights_only=True,map_location=device));head.eval()
        with torch.inference_mode():
            if center_crop:
                from experiment_model import Processor
                batch=Processor.transform(image).unsqueeze(0).to(device)
                features=network.forward_head(network.forward_features(batch),pre_logits=True)
                score=head(features).sigmoid().item()
            else:
                batch=views(image).to(device)
                features=network.forward_head(network.forward_features(batch),pre_logits=True)
                score=probability(head,features.unsqueeze(0)).item()
        del network,head
        if device.type=='cuda':torch.cuda.empty_cache()
    if center_crop:
        return dict(status='completed',score=score,source=dict(repo='真鉴通用图片分类头 / Community Forensics冻结编码器',version=info['version']),note='按训练时的中心裁剪方式提取图像特征，检查整图生成线索。分数为模型输出。')
    return dict(status='completed',score=score,source=dict(repo='亲安商品场景分类头 / Community Forensics冻结编码器',version=info['version']),note='商品场景整图及四个局部视角辅助核验；模型分数不是真伪或诈骗概率，不能证明商品实际损坏。')
