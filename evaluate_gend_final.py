import bootstrap,json,time
from backend.gend import load,score
from check_recent_model import statistics
ROOT=bootstrap.ROOT

def main():
 model,processor,device=load();output={}
 for name,rows in [('fresh180',json.loads((ROOT/'data/video-gend-final/manifest.json').read_text()))]:
  results=[];rejected=[]
  for i,row in enumerate(rows):
   try:p=score(model,processor,device,ROOT/row['path'])
   except ValueError as e:rejected.append(dict(row,reason=str(e)));continue
   results.append(dict(row,score=p,predicted=int(p>=.5)))
   if i%10==0:print(name,i+1,'/',len(rows),flush=True)
  output[name]=dict(metrics=statistics(results),results=results,rejected=rejected)
  (ROOT/'reports/gend-final.json').write_text(json.dumps(output,indent=2))
  print(name,output[name]['metrics'],flush=True)
if __name__=='__main__':main()
