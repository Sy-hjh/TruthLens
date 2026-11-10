"""Frozen SigLIP face-frame candidate: same8uniform frames, fixed preprocessing."""
import bootstrap,json,torch
from PIL import Image
from backend.media import sample_video
from backend.faces import face_views
from check_recent_model import statistics
from transformers import AutoImageProcessor,AutoModelForImageClassification
ROOT=bootstrap.ROOT

def score(model,processor,path,device):
 _,frames=sample_video(path,8);images=[im for _,im in frames]
 images,_=face_views(images);scores=[];fake=next(int(k) for k,v in model.config.id2label.items() if v.lower()=='fake')
 for start in range(0,len(images),2):
  with torch.inference_mode():scores.extend(model(**processor(images=images[start:start+2],return_tensors='pt').to(device)).logits.softmax(-1)[:,fake].cpu().tolist())
 return sum(scores)/len(scores)
def main():
 device='cuda' if torch.cuda.is_available() else 'cpu';folder=ROOT/'models/siglip-face';processor=AutoImageProcessor.from_pretrained(folder,local_files_only=True);model=AutoModelForImageClassification.from_pretrained(folder,local_files_only=True).to(device).eval();out={}
 for name,rows in [('validation',[r for r in json.loads((ROOT/'data/video-fit/manifest.json').read_text()) if r['split']=='val']),('diagnostic',json.loads((ROOT/'data/video-release-check/manifest.json').read_text()))]:
  results=[];rejected=[]
  for i,row in enumerate(rows):
   try:p=score(model,processor,ROOT/row['path'],device)
   except ValueError as e:rejected.append(dict(row,reason=str(e)));continue
   results.append(dict(row,score=p,predicted=int(p>=.5)))
   if i%10==0:print(name,i+1,'/',len(rows),flush=True)
  out[name]=dict(metrics=statistics(results),results=results,rejected=rejected)
  (ROOT/'reports/siglip-face-check.json').write_text(json.dumps(out,indent=2))
 print({k:v['metrics'] for k,v in out.items()})
if __name__=='__main__':main()
