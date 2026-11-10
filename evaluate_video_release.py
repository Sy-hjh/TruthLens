"""Locked post-training check. Never trains or changes thresholds."""
import bootstrap,json,hashlib
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from collect_domain_cases import get
from check_recent_model import statistics
from backend.media import sample_video
ROOT=bootstrap.ROOT

def main():
 import torch
 from transformers import VideoMAEImageProcessor,VideoMAEForVideoClassification
 from backend.faces import face_views
 folder=ROOT/'data/video-release-check';plan=json.loads((folder/'planned.json').read_text());base=f"https://huggingface.co/datasets/{plan['repo']}/resolve/{plan['revision']}/"
 def fetch(row):
  target=folder/Path(row['remote']).name
  if not target.exists():
   data=get(base+row['remote']).content;temp=target.with_suffix('.part');temp.write_bytes(data);temp.replace(target)
  return dict(row,path=target.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(target.read_bytes()).hexdigest())
 rows=[]
 with ThreadPoolExecutor(max_workers=4) as pool:
  for row in pool.map(fetch,plan['rows']):
   rows.append(row)
   if len(rows)%20==0:print('Additional video download',len(rows),flush=True)
 (folder/'manifest.json').write_text(json.dumps(rows,indent=2))
 model=VideoMAEForVideoClassification.from_pretrained(ROOT/'models/video',local_files_only=True).eval();device='cuda' if torch.cuda.is_available() else 'cpu';model=model.to(device);processor=VideoMAEImageProcessor.from_pretrained(ROOT/'models/video',local_files_only=True);fake=next(int(k) for k,v in model.config.id2label.items() if v.lower()=='fake')
 head=torch.nn.Linear(model.classifier.in_features,model.classifier.out_features).to(device);head_path=Path((ROOT/'models/video-face-adapt/best-path.txt').read_text());head.load_state_dict(torch.load(head_path,map_location=device,weights_only=True));head.eval();results=[];baseline=[];rejected=[]
 for i,row in enumerate(rows):
  _,frames=sample_video(ROOT/row['path'],16);images=[im for _,im in frames]
  while len(images)<16:images.append(images[-1])
  with torch.inference_mode():old=model(**processor(images,return_tensors='pt').to(device)).logits.softmax(-1)[0,fake].item()
  baseline.append(dict(row,score=old,predicted=int(old>=.5)))
  try:images,detected=face_views(images)
  except ValueError as e:rejected.append(dict(row,reason=str(e)));continue
  with torch.inference_mode():features=model.fc_norm(model.videomae(**processor(images,return_tensors='pt').to(device)).last_hidden_state.mean(1));score=head(features).softmax(-1)[0,fake].item()
  results.append(dict(row,score=score,predicted=int(score>=.5),face_frames=detected))
  (ROOT/'reports/video-release-progress.json').write_text(json.dumps(dict(results=results,baseline=baseline,rejected=rejected),indent=2))
  if i%10==0:print('Independent video test',i+1,'/',len(rows),flush=True)
 report=dict(metrics=statistics(results),baseline_metrics=statistics(baseline),planned=len(rows),rejected=rejected,results=results,baseline=baseline,head_sha256=hashlib.sha256(head_path.read_bytes()).hexdigest(),threshold=.5,note='100 additional source YouTube IDs excluded from previous train/validation/test/diagnostic. Actor identity separation not verified. Uniface held out from training. Fixed checkpoint and threshold, no training in this script.')
 (ROOT/'reports/video-release-check.json').write_text(json.dumps(report,indent=2));print(report['metrics'],flush=True);print('Old fullframe baseline',report['baseline_metrics'])
if __name__=='__main__':main()
