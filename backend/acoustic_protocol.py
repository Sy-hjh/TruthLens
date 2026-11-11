"""Shared waveform-only evaluation/deployment protocol for VeriSpoof."""
import math
def windows(samples,window=128000,step=64000):
 n=len(samples)
 if n<16000:raise ValueError('至少需要1秒录音')
 last=max(0,n-window);starts=sorted(set(range(0,last+1,step))|{last})
 return [(start,min(start+window,n),samples[start:min(start+window,n)]) for start in starts]
def analyze(model,samples):
 result=[]
 for start,end,chunk in windows(samples):
  output=model.detect(chunk,sr=16000);raw=float(output['score']);value=1/(1+math.exp(-max(-80.,min(80.,raw))))
  result.append(dict(start=start/16000,end=end/16000,score=value,raw_log_likelihood_ratio=raw,threshold=.5,model_label=output['label']))
 return result
