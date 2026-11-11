"""Author preprocessing, pinned weights, local diagnosis; not automatic promotion."""
import bootstrap,json,io
import torch,timm
from safetensors.torch import load_file
from torchvision import transforms as T
from PIL import Image
from check_recent_model import statistics
def main():
 model=timm.create_model('vit_small_patch16_224',img_size=384,num_classes=1,pretrained=False)
 model.load_state_dict({k.removeprefix('vit.'):v for k,v in load_file(str(bootstrap.ROOT/'models/detectra/model.safetensors')).items()},strict=True)
 dev='cuda' if torch.cuda.is_available() else 'cpu';model=model.to(dev).eval()
 tr=T.Compose([T.Resize(440,interpolation=T.InterpolationMode.BILINEAR),T.CenterCrop(384),T.ToTensor(),T.Normalize([.485,.456,.406],[.229,.224,.225])]);out={}
 for name,rows in [('original',json.loads((bootstrap.ROOT/'data/domain-cases/manifest.json').read_text())),('controls',json.loads((bootstrap.ROOT/'data/manual-acceptance/images.json').read_text(encoding='utf-8')))]:
  results=[]
  with torch.inference_mode():
   for i,row in enumerate(rows):
    with Image.open(bootstrap.ROOT/row['path']) as im:p=model(tr(im.convert('RGB')).unsqueeze(0).to(dev)).sigmoid().item()
    results.append(dict(row,score=p,predicted=int(p>=.65)))
    if i%20==0:print(name,i+1,flush=True)
  out[name]=dict(metrics=statistics(results),results=results)
  (bootstrap.ROOT/'reports/detectra-check.json').write_text(json.dumps(out,indent=2));print(name,out[name]['metrics'],flush=True)
if __name__=='__main__':main()
