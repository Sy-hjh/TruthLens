"""Image-only isolated dependency worker. Local files only, no remote code."""
import sys,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def _failure(kind,value,tb):
 import traceback
 (ROOT/'runtime/smaug-worker-error.log').write_text(''.join(traceback.format_exception(kind,value,tb)),encoding='utf-8')
 sys.__excepthook__(kind,value,tb)
sys.excepthook=_failure
import bootstrap
sys.path.insert(0,str(ROOT/'runtime/smaug-packages'))
import transformers.utils.import_utils as iu
import transformers.utils as tu
iu.is_torchaudio_available=lambda:False;tu.is_torchaudio_available=lambda:False
from sentence_transformers import SentenceTransformer
import torch,importlib.util
from PIL import Image,ImageOps
from backend.image_regions import official_view_layout
def main():
 source=json.loads((ROOT/'models/smaug/source.json').read_text(encoding='utf-8'))
 if hashlib.sha256((ROOT/'models/smaug/model.safetensors').read_bytes()).hexdigest()!=source['sha256']:raise RuntimeError('Image weight hash mismatch')
 for name,digest in source.get('files',{}).items():
  if hashlib.sha256((ROOT/'models/smaug'/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Image config or head hash mismatch')
 spec=importlib.util.spec_from_file_location('smaug_reviewed',ROOT/'vendor/smaug/smaug_image_detect.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 device='cuda' if torch.cuda.is_available() else 'cpu'
 st=SentenceTransformer(str(ROOT/'models/smaug'),local_files_only=True,device=device,config_kwargs={'audio_config':None},model_kwargs={'torch_dtype':torch.bfloat16 if device=='cuda' else torch.float32})
 model=module.SmaugImageDetect(st)
 with Image.open(sys.argv[1]) as image:
  image=ImageOps.exif_transpose(image).convert('RGB');crops=module.views(image,3);layout=official_view_layout(image)
  with torch.inference_mode():
   logits=st.encode([{'image':crop} for crop in crops],batch_size=3,convert_to_tensor=True).float().view(-1)
   value=torch.sigmoid(logits.mean()).item();scores=logits.sigmoid().tolist()
  axis='横向' if image.width>=image.height else '纵向'
  trace=[dict(label=axis+label,score=float(score),logit=float(logit)) for label,score,logit in zip(['起始视图','中央视图','末端视图'],scores,logits.tolist())]
 print(json.dumps({'score':value,'views':trace,'sampling':layout,'aggregation':'sigmoid(mean(view_logits))'}),flush=True)
if __name__=='__main__':
 try:main()
 except Exception:
  import traceback
  (ROOT/'runtime/smaug-worker-error.log').write_text(traceback.format_exc(),encoding='utf-8')
  raise
