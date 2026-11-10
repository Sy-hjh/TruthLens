"""Small local adapter for the official 2025 Community Forensics checkpoint."""
from types import SimpleNamespace
from pathlib import Path
import torch
from safetensors.torch import save_file
from torchvision import transforms as T
from check_recent_model import load

class Experiment(torch.nn.Module):
    def __init__(self):
        super().__init__(); self.network=load()
        self.config=SimpleNamespace(id2label={0:'human',1:'ai'})
    @property
    def classifier(self): return self.network.head
    def forward(self,pixel_values,labels=None):
        z=self.network(pixel_values)
        logits=torch.cat([-z/2,z/2],dim=1)
        loss=torch.nn.functional.cross_entropy(logits,labels) if labels is not None else None
        return SimpleNamespace(logits=logits,loss=loss)
    def save_pretrained(self,path):
        path=Path(path);path.mkdir(parents=True,exist_ok=True)
        save_file({'vit.'+k:v.detach().contiguous().cpu() for k,v in self.network.state_dict().items()},str(path/'model.safetensors'))

class Processor:
    transform=T.Compose([T.Resize(256),T.CenterCrop(224),T.ToTensor(),T.Normalize([.485,.456,.406],[.229,.224,.225])])
    def __call__(self,images,return_tensors='pt'):
        from transformers import BatchFeature
        return BatchFeature({'pixel_values':torch.stack([self.transform(im) for im in images])})
    def save_pretrained(self,path):
        Path(path,'preprocessing.txt').write_text('Resize short edge256; CenterCrop224; RGB; ImageNet normalization; fake=sigmoid(logit)',encoding='utf-8')
