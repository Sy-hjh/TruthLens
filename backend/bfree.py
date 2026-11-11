"""Audited local B-Free adapter; original five embedding crops, no resizing."""
import importlib.util
import bootstrap
import torch
import timm
from torchvision import transforms as T

def load():
    spec=importlib.util.spec_from_file_location('bfree_wrapper',bootstrap.ROOT/'vendor/bfree/code_networks_wrapper5crops.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    net=timm.create_model('vit_base_patch14_reg4_dinov2.lvd142m',num_classes=1,pretrained=False)
    model=module.Wrapper5crops(net,504)
    state=torch.load(bootstrap.ROOT/'models/bfree/model_epoch_best.pth',map_location='cpu',weights_only=True)
    model.load_state_dict(state['model'])
    device='cuda' if torch.cuda.is_available() else 'cpu'
    transform=T.Compose([T.ToTensor(),T.Normalize([.485,.456,.406],[.229,.224,.225])])
    return model.eval().to(device),transform,device

def score(model,transform,device,image):
    with torch.inference_mode():
        return model(transform(image.convert('RGB')).unsqueeze(0).to(device)).sigmoid().item()
