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
from PIL import Image
def main():
 source=json.loads((ROOT/'models/smaug/source.json').read_text(encoding='utf-8'))
 if hashlib.sha256((ROOT/'models/smaug/model.safetensors').read_bytes()).hexdigest()!=source['sha256']:raise RuntimeError('Image weight hash mismatch')
 for name,digest in source.get('files',{}).items():
  if hashlib.sha256((ROOT/'models/smaug'/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Image config or head hash mismatch')
 spec=importlib.util.spec_from_file_location('smaug_reviewed',ROOT/'vendor/smaug/smaug_image_detect.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 device='cuda' if torch.cuda.is_available() else 'cpu'
 st=SentenceTransformer(str(ROOT/'models/smaug'),local_files_only=True,device=device,config_kwargs={'audio_config':None},model_kwargs={'torch_dtype':torch.bfloat16 if device=='cuda' else torch.float32})
 model=module.SmaugImageDetect(st)
 with Image.open(sys.argv[1]) as image:value=model(image.convert('RGB'),batch_size=3)
 print(json.dumps({'score':value}),flush=True)
if __name__=='__main__':
 try:main()
 except Exception:
  import traceback
  (ROOT/'runtime/smaug-worker-error.log').write_text(traceback.format_exc(),encoding='utf-8')
  raise
