"""External product-domain diagnostic; never trains or changes website weights."""
import bootstrap,json,io,csv,hashlib,time,base64,html
from pathlib import Path
import torch
from PIL import Image
from torchvision import transforms as T
from check_recent_model import load,statistics
ROOT=bootstrap.ROOT
def main():
    folder=ROOT/'data/domain-cases';rows=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    target=ROOT/'reports/domain-evaluation.json'
    data=(ROOT/'models/balanced-v1/best/model.safetensors').read_bytes();digest=hashlib.sha256(data).hexdigest()
    weights=ROOT/'models/releases'/digest/'model.safetensors';weights.parent.mkdir(parents=True,exist_ok=True)
    if not weights.exists():weights.write_bytes(data)
    model=load(weights);device=next(model.parameters()).device
    transform=T.Compose([T.Resize(256),T.CenterCrop(224),T.ToTensor(),T.Normalize([.485,.456,.406],[.229,.224,.225])])
    results=[]
    with torch.inference_mode():
        for i,row in enumerate(rows):
            with Image.open(ROOT/row['path']) as original:im=original.convert('RGB')
            clean=model(transform(im).unsqueeze(0).to(device)).sigmoid().item()
            buffer=io.BytesIO();im.save(buffer,format='JPEG',quality=60)
            with Image.open(io.BytesIO(buffer.getvalue())) as compressed:
                degraded=model(transform(compressed.convert('RGB')).unsqueeze(0).to(device)).sigmoid().item()
            results.append(dict(row,score=clean,predicted=int(clean>=.5),jpeg60_score=degraded,jpeg60_predicted=int(degraded>=.5)))
            if (i+1)%20==0:print('Whole-image model',i+1,'/',len(rows),flush=True)
    del model
    if torch.cuda.is_available():torch.cuda.empty_cache()
    # Stratified 60-image local-edit check, 30 real controls + 30 AI edits.
    selected=[]
    for kind in ('published-real-undamaged','published-real-damaged'):
        pool=[r for r in results if r['kind']==kind]
        selected.extend(pool[::2][:15])
    generators=sorted(set(r['generator'] for r in results if r['label']==1))
    for generator in generators:
        pool=[r for r in results if r['generator']==generator]
        selected.extend(pool[::6][:5])
    from backend.tamper import predict
    tamper=[];heatmaps=ROOT/'reports/domain-heatmaps';heatmaps.mkdir(exist_ok=True)
    for i,row in enumerate(selected):
        with Image.open(ROOT/row['path']) as im:output=predict(im.convert('RGB'))
        item=dict(path=row['path'],label=row['label'],kind=row['kind'],generator=row['generator'],score=output['score'],predicted=int(output['score']>=.5))
        # Store a few genuine model maps, never fake annotations.
        if i<6 or i%5==0:
            uri=output.get('map_png','')
            if uri.startswith('data:image/png;base64,'):
                path=heatmaps/(Path(row['path']).stem+'.png');path.write_bytes(base64.b64decode(uri.split(',',1)[1]));item['map']=path.relative_to(ROOT).as_posix()
        tamper.append(item)
        print('Local-edit model',i+1,'/',len(selected),flush=True)
        (ROOT/'reports/domain-tamper-progress.json').write_text(json.dumps(tamper,ensure_ascii=False,indent=2),encoding='utf-8')
    compressed=[dict(r,predicted=r['jpeg60_predicted']) for r in results]
    report=dict(weights_sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),threshold=.5,whole_image=statistics(results),jpeg60=statistics(compressed),by_kind={k:statistics([r for r in results if r['kind']==k]) for k in sorted(set(r['kind'] for r in results))},by_generator={g:statistics([r for r in results if r['generator']==g]) for g in generators},local_edit_60=statistics(tamper),local_edit_results=tamper,results=results,note='External diagnostic only. AI-edited images are a different task from whole-image generation. Source author labels inherited; not verified fraud. Convenience sample, no training on these cases.')
    target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (ROOT/'reports/domain-results.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.writer(f);writer.writerow(['文件','类别','来源标签','生成器','整图分数','整图预测','JPEG60分数','来源'])
        for r in results:writer.writerow([r['path'],r['category'],r['kind'],r['generator'],r['score'],r['predicted'],r['jpeg60_score'],r['source_url']])
    print(json.dumps({k:report[k] for k in ('whole_image','jpeg60','local_edit_60')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
