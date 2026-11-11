"""Load reviewed local audio-forensic code with isolated modern Transformers."""
import bootstrap,sys,json
from pathlib import Path
def load():
 root=bootstrap.ROOT;sys.path.insert(0,str(root/'runtime/smaug-packages'))
 import transformers.utils.import_utils as iu,transformers.utils as tu
 iu.is_torchaudio_available=lambda:False;tu.is_torchaudio_available=lambda:False
 sys.path.insert(0,str(root/'vendor/verispoof/runtime_code'))
 from verispoof import VeriSpoof
 return VeriSpoof.from_pretrained(str(root/'models/verispoof'))
