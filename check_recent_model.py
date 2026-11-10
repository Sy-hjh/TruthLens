"""Author-equivalent ViT inference, local files only, no automatic website promotion."""
import bootstrap
import torch,timm,json,argparse
from PIL import Image
from safetensors.torch import load_file
from torchvision import transforms as T

def statistics(results):
    real=[r for r in results if r['label']==0];fake=[r for r in results if r['label']==1]
    fp=sum(r['predicted']==1 for r in real);fn=sum(r['predicted']==0 for r in fake)
    fpr=fp/len(real) if real else None;fnr=fn/len(fake) if fake else None
    return dict(n=len(results),real_count=len(real),fake_count=len(fake),false_positives=fp,false_negatives=fn,real_false_positive_rate=fpr,fake_miss_rate=fnr,balanced_accuracy=1-(fpr+fnr)/2 if real and fake else None,accuracy=sum(r['label']==r['predicted'] for r in results)/len(results) if results else None)

def load(weights=None):
    model=timm.create_model('vit_small_patch16_224.augreg_in21k_ft_in1k',pretrained=False,num_classes=1)
    state=load_file(str(weights or bootstrap.ROOT/'models/community/model.safetensors'))
    model.load_state_dict({k.removeprefix('vit.'):v for k,v in state.items()},strict=True)
    return model.eval().to('cuda' if torch.cuda.is_available() else 'cpu')

def main():
    p=argparse.ArgumentParser();p.add_argument('manifest',type=str);p.add_argument('--output',default='reports/community-pilot.json');p.add_argument('--weights');p.add_argument('--split',choices=['train','val','test']);a=p.parse_args()
    model=load(a.weights);device=next(model.parameters()).device
    # Author evaluation uses Resize square and ImageNet mean/std. Verify against eval.py before comparing.
    transform=T.Compose([T.Resize(256),T.CenterCrop(224),T.ToTensor(),T.Normalize([.485,.456,.406],[.229,.224,.225])])
    rows=json.loads((bootstrap.ROOT/a.manifest).read_text(encoding='utf-8'));results=[]
    if a.split:rows=[r for r in rows if r.get('split')==a.split]
    if not rows:raise ValueError('No matching samples')
    with torch.inference_mode():
        for row in rows:
            with Image.open(bootstrap.ROOT/row['path']) as im:x=transform(im.convert('RGB')).unsqueeze(0).to(device)
            score=model(x).sigmoid().item();results.append(dict(path=row['path'],group=row.get('group','unknown') if row['label']==1 else 'real-photos',label=row['label'],score=score,predicted=int(score>=.5)))
    groups=sorted(set(r['group'] for r in results))
    output=dict(results=results,**statistics(results),by_group={g:statistics([r for r in results if r['group']==g]) for g in groups},note='pilot only; source overlap possible; not elderly/GPT benchmark')
    target=bootstrap.ROOT/a.output;target.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:v for k,v in output.items() if k not in ('results','by_group')},ensure_ascii=False))

if __name__=='__main__':main()
