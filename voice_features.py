"""Frozen acoustic features and matched clean/AAC/telephone augmentations."""
import bootstrap,hashlib,json,subprocess,math
import numpy as np,torch,soundfile as sf
from scipy.signal import resample_poly
from backend.voice_forensics import waveform
ROOT=bootstrap.ROOT
def cache_folder():
 source=json.loads((ROOT/'models/audio-forensics/source.json').read_text());return ROOT/'runtime/voice-features'/(source['sha256'][:16]+'-clean-aac32-phone8-v1')
def cache_path(row):return cache_folder()/(row['sha256']+'.npy')
def audio(path):
 x,sr=sf.read(path,dtype='float32',always_2d=True);x=x.mean(1)
 if sr!=16000:
  g=math.gcd(sr,16000);x=resample_poly(x,16000//g,sr//g)
 return np.array(x,dtype=np.float32)
def variants(x):
 import imageio_ffmpeg
 ff=imageio_ffmpeg.get_ffmpeg_exe()
 encoded=subprocess.run([ff,'-v','error','-f','f32le','-ar','16000','-ac','1','-i','pipe:0','-c:a','aac','-b:a','32k','-f','adts','pipe:1'],input=x.tobytes(),capture_output=True,check=True).stdout
 decoded=subprocess.run([ff,'-v','error','-f','aac','-i','pipe:0','-f','f32le','-ar','16000','-ac','1','pipe:1'],input=encoded,capture_output=True,check=True).stdout
 return [x,np.frombuffer(decoded,dtype=np.float32).copy(),resample_poly(resample_poly(x,1,2),2,1).astype(np.float32)]
def features(model,signals,device):
 x=torch.cat([waveform(s) for s in signals]).to(device)
 with torch.inference_mode():
  hs=list(model.wavlm(x,output_hidden_states=True).hidden_states[1:]);f=model.pool(hs).cpu().numpy()
 return f
