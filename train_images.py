"""Local, resumable classifier-head experiment. Never auto-promotes to website."""
import bootstrap
import argparse, hashlib, json, signal
from pathlib import Path
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epochs', type=int, default=10, help='Total target epochs, including completed epochs')
    parser.add_argument('--batch-size', type=int, default=4)
    parser.add_argument('--manifest', type=Path, default=bootstrap.ROOT/'data/training/manifest.json')
    parser.add_argument('--output', type=Path, default=bootstrap.ROOT/'models/experiment-head')
    parser.add_argument('--max-steps', type=int, default=0, help='Stop after this many new updates; 0 unlimited')
    parser.add_argument('--patience',type=int,default=0,help='Stop after N validation checks without improvement; 0 disables')
    args=parser.parse_args()
    torch.manual_seed(42)
    rows=json.loads(args.manifest.read_text(encoding='utf-8'))
    fingerprint=hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    train=[r for r in rows if r['split']=='train']; val=[r for r in rows if r['split']=='val']
    if not train or not val or {r['label'] for r in train}!={0,1} or {r['label'] for r in val}!={0,1}: raise ValueError('Training and validation must both contain real and fake samples')
    if {r['path'] for r in train}&{r['path'] for r in val}:raise ValueError('Same file appears in training and validation')
    device='cuda' if torch.cuda.is_available() else 'cpu'
    from experiment_model import Experiment,Processor
    processor=Processor()
    model=Experiment().to(device)
    if not hasattr(model,'classifier'): raise ValueError('Unsupported classifier architecture')
    for parameter in model.parameters(): parameter.requires_grad=False
    for parameter in model.classifier.parameters(): parameter.requires_grad=True
    optimizer=torch.optim.AdamW(model.classifier.parameters(),lr=1e-4)
    args.output.mkdir(parents=True,exist_ok=True)
    from checkpoint_io import load_latest,save_checkpoint,acquire_training_lock
    training_lock=acquire_training_lock(args.output)
    checkpoint=args.output/'last.pt'; epoch=cursor=step=0; best=-1.0
    best_loss=float('inf');stale=0
    saved=load_latest(checkpoint)
    if saved is not None:
        if saved.get('base')!='community-2025' or saved['manifest']!=fingerprint or saved['batch_size']!=args.batch_size: raise ValueError('Model, manifest or batch size changed; use a new --output')
        model.classifier.load_state_dict(saved['head']); optimizer.load_state_dict(saved['optimizer'])
        epoch,cursor,step,best=saved['epoch'],saved['cursor'],saved['step'],saved['best']
        best_loss=saved.get('best_loss',float('inf'));stale=saved.get('stale',0)
        print(f'Resuming epoch={epoch+1} sample={cursor} total_updates={step}',flush=True)
    stopped=False
    def request_stop(*_):
        nonlocal stopped
        stopped=True
        print('Stop requested: finishing current update and saving. Please wait.',flush=True)
    signal.signal(signal.SIGINT,request_stop)
    if hasattr(signal,'SIGBREAK'): signal.signal(signal.SIGBREAK,request_stop)
    def save():
        save_checkpoint(dict(base='community-2025',head=model.classifier.state_dict(),optimizer=optimizer.state_dict(),epoch=epoch,cursor=cursor,step=step,best=best,best_loss=best_loss,stale=stale,manifest=fingerprint,batch_size=args.batch_size),checkpoint)
    fake=[int(k) for k,v in model.config.id2label.items() if v.lower() in ('ai','fake','artificial')][0]
    counts=[sum(r['label']==i for r in train) for i in (0,1)]
    class_weights=torch.tensor([len(train)/(2*counts[0]),len(train)/(2*counts[1])],device=device)
    if fake==0:class_weights=class_weights.flip(0)
    def batch(items):
        images=[]
        for r in items:
            with Image.open(bootstrap.ROOT/r['path']) as im: images.append(im.convert('RGB'))
        labels=torch.tensor([fake if r['label']==1 else 1-fake for r in items],device=device)
        return processor(images=images,return_tensors='pt').to(device),labels
    new_steps=0
    while epoch<args.epochs and not stopped:
        order=torch.randperm(len(train),generator=torch.Generator().manual_seed(42+epoch)).tolist()
        model.eval() # frozen backbone and deterministic dropout-free resume
        while cursor<len(order) and not stopped:
            ids=order[cursor:cursor+args.batch_size]; x,y=batch([train[i] for i in ids])
            optimizer.zero_grad(set_to_none=True)
            loss=torch.nn.functional.cross_entropy(model(**x).logits,y,weight=class_weights); loss.backward(); optimizer.step()
            cursor+=len(ids); step+=1; new_steps+=1; save()
            stop_file=args.output/'STOP'
            if stop_file.exists():
                stopped=True; stop_file.unlink()
            print(f'epoch={epoch+1}/{args.epochs} samples={cursor}/{len(train)} step={step} loss={loss.item():.5f}',flush=True)
            if args.max_steps and new_steps>=args.max_steps: stopped=True
        if cursor==len(order):
            correct=[0,0]; total=[0,0];validation_loss=0.0
            with torch.inference_mode():
                for r in val:
                    x,y=batch([r]); logits=model(**x).logits;pred=int(logits.argmax(-1)[0]); label=r['label']
                    validation_loss+=torch.nn.functional.cross_entropy(logits,y).item()
                    total[label]+=1; correct[label]+=int(pred==int(y[0]))
            balanced=sum(correct[i]/total[i] for i in (0,1))/2 if all(total) else 0
            validation_loss/=len(val)
            if balanced>best or (balanced==best and validation_loss<best_loss-0.0001):
                best=balanced;best_loss=validation_loss;stale=0;model.save_pretrained(args.output/'best'); processor.save_pretrained(args.output/'best')
            else:stale+=1
            metrics=dict(epoch=epoch+1,step=step,balanced_accuracy=balanced,val_loss=validation_loss,real_false_positive_rate=1-correct[0]/total[0],fake_miss_rate=1-correct[1]/total[1],correct=correct,total=total,stale=stale)
            with (args.output/'history.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(metrics)+'\n')
            print(f'validation balanced_accuracy={balanced:.4f}; exploratory only',flush=True)
            epoch+=1; cursor=0; save()
            print('验证：真人误报率=%.2f%%，AI漏检率=%.2f%%，验证损失=%.4f，连续未改善=%d'%(100*metrics['real_false_positive_rate'],100*metrics['fake_miss_rate'],validation_loss,stale),flush=True)
            if args.patience and stale>=args.patience:
                print('验证集连续未改善，自动停止。检查best模型，不要靠追加轮数硬练。',flush=True);stopped=True
    save()
    print(f'Saved checkpoint in {args.output} (last.pt or recovery copy). Same command resumes.',flush=True)

if __name__=='__main__': main()
