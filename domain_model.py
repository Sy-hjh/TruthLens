"""Frozen ViT features, global and four local views, multiple-instance head."""
import io
import torch
from torchvision import transforms as T
TRANSFORM=T.Compose([T.Resize((224,224)),T.ToTensor(),T.Normalize([.485,.456,.406],[.229,.224,.225])])
def views(image,quality=None):
    image=image.convert('RGB')
    if quality:
        buffer=io.BytesIO();image.save(buffer,format='JPEG',quality=quality);image=__import__('PIL.Image',fromlist=['open']).open(io.BytesIO(buffer.getvalue())).convert('RGB')
    w,h=image.size;s=max(16,int(min(w,h)*.7))
    crops=[image]+[image.crop((x,y,x+s,y+s)) for x,y in ((0,0),(w-s,0),(0,h-s),(w-s,h-s))]
    return torch.stack([TRANSFORM(im) for im in crops])
def aggregate(logits):
    # Global evidence and strongest two patch responses, trained jointly.
    return .5*logits[:,0]+.5*logits[:,1:].topk(2,dim=1).values.mean(1)
def probability(head,features):return aggregate(head(features).squeeze(-1)).sigmoid()
def make_head(kind='linear'):
    if kind=='linear':return torch.nn.Linear(384,1)
    if kind=='mlp':return torch.nn.Sequential(torch.nn.LayerNorm(384),torch.nn.Linear(384,128),torch.nn.GELU(),torch.nn.Dropout(.1),torch.nn.Linear(128,1))
    raise ValueError('Unknown head architecture')
