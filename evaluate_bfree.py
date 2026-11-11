"""Diagnostic only: paired local edits, original and JPEG60. No model promotion."""
import bootstrap,json,io
from PIL import Image
from backend.bfree import load,score
from check_recent_model import statistics

def main():
 model,transform,device=load();out={}
 rows=json.loads((bootstrap.ROOT/'data/domain-cases/manifest.json').read_text())
 for name in ['original','jpeg60']:
  results=[]
  for i,row in enumerate(rows):
   with Image.open(bootstrap.ROOT/row['path']) as opened:
    im=opened.convert('RGB')
   if name=='jpeg60':
    buf=io.BytesIO();im.save(buf,format='JPEG',quality=60);buf.seek(0);im=Image.open(buf).convert('RGB')
   p=score(model,transform,device,im);results.append(dict(row,score=p,predicted=int(p>=.5)))
   if i%10==0:print(name,i+1,'/',len(rows),flush=True)
  out[name]=dict(metrics=statistics(results),results=results)
  (bootstrap.ROOT/'reports/bfree-check.json').write_text(json.dumps(out,indent=2))
  print(name,out[name]['metrics'],flush=True)
if __name__=='__main__':main()
