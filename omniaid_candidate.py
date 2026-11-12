"""Local, strict author OmniAID-v2 inference; no remote code or unsafe pickle."""
import bootstrap,sys,ast,json,hashlib,types,gc,argparse
import numpy as np,torch
from PIL import Image,ImageOps
ROOT=bootstrap.ROOT
def sha256_file(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  while block:=stream.read(8*1024*1024):h.update(block)
 return h.hexdigest()
def load(device=None,implementation='clean'):
 print('Loading local CLIP inference architecture',flush=True)
 from transformers import CLIPModel,CLIPConfig
 folder=ROOT/'models/omniaid';source=json.loads((folder/'source.json').read_text(encoding='utf-8'));path=folder/'checkpoint_omniaid_v2.pth'
 print('Verifying image checkpoint by bounded streaming hash',flush=True)
 assert sha256_file(path)==source['sha256'][path.name],'OmniAID checksum mismatch'
 backbone_source=json.loads((folder/'backbone-source.json').read_text());config_path=folder/'clip-config.json';assert hashlib.sha256(config_path.read_bytes()).hexdigest()==backbone_source['sha256']
 relative='reward/omniaid.py' if implementation=='clean' else 'models/OmniAID.py';script=ROOT/'runtime/omniaid-source'/relative;body=script.read_bytes();tree=json.loads((ROOT/'runtime/omniaid-tree.json').read_text());entry=next(r for r in tree['tree'] if r['path']==relative);assert hashlib.sha1(b'blob '+str(len(body)).encode()+b'\0'+body).hexdigest()==entry['sha']
 # The checkpoint contains the entire frozen router backbone and trainable network.
 # Construct architecture on meta, skip redundant download/SVD initialization, then
 # strictly assign ALL saved tensors. No randomly initialized layer may be scored.
 text=body.decode();text=text.replace('CLIPModel.from_pretrained(pretrained_path).vision_model','CLIPModel(CLIPConfig.from_json_file(CLIP_CONFIG)).vision_model');text=text.replace('self.load_and_replace_from_pretrained(self.feature_extractor)','pass # All tensors must be loaded strictly below')
 namespace=dict(CLIPConfig=CLIPConfig,CLIP_CONFIG=str(config_path));exec(compile(text,str(script),'exec'),namespace)
 cfg=json.loads((folder/'config_omniaid_v2.json').read_text(encoding='utf-8'));cfg['CLIP_path']='offline'
 # Official reward/clean_test.py explicitly supplies this omitted JSON field.
 cfg.setdefault('is_hybrid',True);config=types.SimpleNamespace(**cfg)
 print('Constructing architecture without random weight allocation',flush=True)
 with torch.device('meta'):model=namespace['OmniAID'](config)
 print('Loading trained checkpoint tensors',flush=True)
 # argparse.Namespace is a metadata container saved by the official training script.
 # No author model class or arbitrary downloaded globals are permitted.
 with torch.serialization.safe_globals([argparse.Namespace]):state=torch.load(path,map_location='cpu',weights_only=True,mmap=True)
 print('OmniAID checkpoint fields',list(state)[:8],flush=True)
 if 'model' in state:state=state['model']
 if all(k.startswith('module.') for k in state):state={k[7:]:v for k,v in state.items()}
 model.load_state_dict(state,strict=True,assign=True)
 # position_ids are nonpersistent buffers and are not stored in CLIP checkpoints.
 for module in model.modules():
  if hasattr(module,'position_ids') and module.position_ids.device.type=='meta':module.position_ids=torch.arange(module.position_ids.shape[-1]).expand((1,-1))
 if any(p.device.type=='meta' for p in model.parameters()):raise RuntimeError('Unloaded image inference parameter')
 device=device or ('cuda' if torch.cuda.is_available() else 'cpu');model=model.to(device=device,dtype=torch.float32).eval();model.requires_grad_(False);del state;gc.collect();print('Strict OmniAID-v2 inference ready',flush=True);return model

def predict(model,image):
 image=ImageOps.exif_transpose(image).convert('RGB').resize((336,336),Image.Resampling.BILINEAR)
 x=torch.from_numpy(np.array(image).copy()).permute(2,0,1).float()/255
 x=(x-torch.tensor([.48145466,.4578275,.40821073])[:,None,None])/torch.tensor([.26862954,.26130258,.27577711])[:,None,None]
 device=next(model.parameters()).device
 with torch.inference_mode():
  output=model(x.unsqueeze(0).to(device));value=float((output['prob'] if isinstance(output,dict) else output)[0])
 if not np.isfinite(value) or not 0<=value<=1:raise RuntimeError('Invalid OmniAID output')
 return value
if __name__=='__main__':
 torch.set_num_threads(2);model=load()
 with Image.open(ROOT/'data/manual-acceptance/generated-kitchen.png') as image:print('Actual synthetic fixture score',predict(model,image),flush=True)
