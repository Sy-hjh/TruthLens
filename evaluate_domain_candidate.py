"""Fixed-threshold held-out comparison, no threshold selection on these cases."""
import bootstrap,json,hashlib,argparse
from pathlib import Path
import torch
from PIL import Image
from check_recent_model import load,statistics
from domain_model import views,probability,make_head
ROOT=bootstrap.ROOT
def main():
    if (ROOT/'runtime/STOP_OPTIMIZATION').exists():print('已请求停止优化');return
    rows=json.loads((ROOT/'data/domain-cases/manifest.json').read_text(encoding='utf-8'))
    parser=argparse.ArgumentParser();parser.add_argument('--model',default='models/domain-v1');parser.add_argument('--output',default='reports/domain-candidate.json');args=parser.parse_args()
    selection=json.loads((ROOT/args.model/'selection.json').read_text())
    weights=ROOT/selection['base_weights_relative']
    assert hashlib.sha256(weights.read_bytes()).hexdigest()==selection['base_weights_sha256']
    network=load(weights);device=next(network.parameters()).device
    head=make_head(selection.get('head_type','linear')).to(device);head.load_state_dict(torch.load(ROOT/selection['head_file'],weights_only=True,map_location=device));head.eval()
    results=[]
    with torch.inference_mode():
        for i,row in enumerate(rows):
            with Image.open(ROOT/row['path']) as im:batch=torch.cat([views(im,q) for q in (None,60)]).to(device)
            features=network.forward_head(network.forward_features(batch),pre_logits=True).reshape(2,5,-1)
            scores=probability(head,features).cpu().tolist()
            results.append(dict(row,score=scores[0],predicted=int(scores[0]>=.5),jpeg60_score=scores[1],jpeg60_predicted=int(scores[1]>=.5)))
            if i%20==0:print('场景候选测试',i+1,'/',len(rows),flush=True)
    compressed=[dict(r,predicted=r['jpeg60_predicted']) for r in results]
    report=dict(selection=selection,clean=statistics(results),jpeg60=statistics(compressed),results=results,threshold=.5,note='Previously observed external diagnostic set, not a new independent test; fixed recipe and validation-only model selection. Review variants correlated.')
    (ROOT/args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ('clean','jpeg60')},ensure_ascii=False))
if __name__=='__main__':main()
