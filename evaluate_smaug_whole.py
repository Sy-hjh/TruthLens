"""Isolated modern image model experiment; no website dependency upgrades."""
import bootstrap,sys,json,importlib.util
from PIL import Image
sys.path.insert(0,str(bootstrap.ROOT/'runtime/smaug-packages'))
# Image-only run: the system torchaudio binary is incompatible with installed torch.
import transformers.utils.import_utils as iu
import transformers.utils as tu
iu.is_torchaudio_available=lambda:False;tu.is_torchaudio_available=lambda:False
spec=importlib.util.spec_from_file_location('smaug_checked',bootstrap.ROOT/'vendor/smaug/smaug_image_detect.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
from check_recent_model import statistics
def main():
 model=module.SmaugImageDetect.from_pretrained(str(bootstrap.ROOT/'models/smaug'))
 out={}
 cohorts=[('controls',json.loads((bootstrap.ROOT/'data/manual-acceptance/images.json').read_text(encoding='utf-8'))),('whole_image_val',[r for r in json.loads((bootstrap.ROOT/'data/balanced-v1/manifest.json').read_text(encoding='utf-8')) if r['split']=='val'])]
 for name,rows in cohorts:
  results=[]
  for i,row in enumerate(rows):
   with Image.open(bootstrap.ROOT/row['path']) as im:p=model(im.convert('RGB'),batch_size=3)
   results.append(dict(row,score=p,predicted=int(p>=.5)))
   if i%10==0:print(name,i+1,'/',len(rows),flush=True)
  out[name]=dict(metrics=statistics(results),results=results)
  (bootstrap.ROOT/'reports/smaug-whole-check.partial.json').write_text(json.dumps(out,indent=2));print(name,out[name]['metrics'],flush=True)
 (bootstrap.ROOT/'reports/smaug-whole-check.partial.json').replace(bootstrap.ROOT/'reports/smaug-whole-check.json')
if __name__=='__main__':main()
