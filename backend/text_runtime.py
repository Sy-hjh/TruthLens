"""Bounded CPU cache for the same verified local text model; no input caching."""
import json,hashlib,gc,ctypes,os
from bootstrap import ROOT
_cached=None
_key=None
_verified=set()

def free_memory():
 if os.name=='nt':
  class Memory(ctypes.Structure):
   _fields_=[('length',ctypes.c_ulong),('load',ctypes.c_ulong)]+[(n,ctypes.c_ulonglong) for n in ['total','available','page_total','page_available','virtual_total','virtual_available','extended']]
  value=Memory();value.length=ctypes.sizeof(value);ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value));return value.available
 return 0

def acquire(path,device):
 global _cached,_key
 import torch
 from transformers import AutoTokenizer,AutoModelForCausalLM
 source=json.loads((path/'source.json').read_text(encoding='utf-8'));items=[]
 for name,expected in source['sha256'].items():
  file=path/name;stat=file.stat();key=(str(file),stat.st_size,stat.st_mtime_ns,expected);items.append(key)
  if name.endswith('.safetensors') and key not in _verified:
   h=hashlib.sha256()
   with file.open('rb') as stream:
    while block:=stream.read(8*1024*1024):h.update(block)
   if h.hexdigest()!=expected:raise RuntimeError('Text checkpoint hash mismatch')
   _verified.add(key)
 key=tuple(items)
 if _cached is not None and _key==key:
  tokenizer,model=_cached;_cached=None;return tokenizer,model.to(device),key
 _cached=None;gc.collect()
 tokenizer=AutoTokenizer.from_pretrained(path,local_files_only=True,trust_remote_code=False)
 model=AutoModelForCausalLM.from_pretrained(path,local_files_only=True,trust_remote_code=False,use_safetensors=True,torch_dtype=torch.float16 if device=='cuda' else torch.float32).to(device).eval()
 return tokenizer,model,key

def release(tokenizer,model,key):
 global _cached,_key
 import torch
 model.cpu();gc.collect();torch.cuda.empty_cache()
 if free_memory()>3*1024**3:_cached=(tokenizer,model);_key=key
 else:_cached=None;_key=None
