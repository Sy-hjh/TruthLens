"""Compare old and modern audio detectors on disclosed matched Mandarin diagnostic."""
import bootstrap,json,tempfile,torch
from pathlib import Path
from backend.detector import audio_samples,classify
from backend.voice_forensics import load_model,waveform
from check_recent_model import statistics
ROOT=bootstrap.ROOT

def main():
 rows=json.loads((ROOT/'data/audio-check/manifest.json').read_text(encoding='utf-8'));device='cuda' if torch.cuda.is_available() else 'cpu';net=load_model().to(device);results=[]
 for i,row in enumerate(rows):
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as temp:samples=audio_samples(ROOT/row['path'],temp)
  with torch.inference_mode():score=1-net(waveform(samples).to(device)).sigmoid().item()
  results.append(dict(row,score=score,predicted=int(score>=.5)))
  print('Modern Mandarin diagnostic',i+1,'/',len(rows),flush=True)
 del net
 if device=='cuda':torch.cuda.empty_cache()
 from transformers import AutoFeatureExtractor,AutoModelForAudioClassification
 processor=AutoFeatureExtractor.from_pretrained(ROOT/'models/audio',local_files_only=True);old=AutoModelForAudioClassification.from_pretrained(ROOT/'models/audio',local_files_only=True).to(device).eval();fake=next(int(k) for k,v in old.config.id2label.items() if v.lower() in ('fake','artificial','ai'));baseline=[]
 for i,row in enumerate(rows):
  with tempfile.TemporaryDirectory(dir=ROOT/'runtime') as temp:samples=audio_samples(ROOT/row['path'],temp)
  with torch.inference_mode():score=old(**processor(samples,sampling_rate=16000,return_tensors='pt',padding=True).to(device)).logits.softmax(-1)[0,fake].item()
  baseline.append(dict(row,score=score,predicted=int(score>=.5)));print('Original audio comparison',i+1,'/',len(rows),flush=True)
 report=dict(metrics=statistics(results),baseline_metrics=statistics(baseline),results=results,baseline=baseline,threshold=.5,note='60 matched-content Mandarin pairs, real public telephone speech vs3 generic standard Edge TTS voices. No modern voice-cloning or elderly-domain claim; unknown pretraining overlap and speaker IDs. Fixed0.5 diagnostic threshold.')
 validation=[r for r in results if int(r['group'])<20];test=[r for r in results if int(r['group'])>=20]
 candidates=sorted({0.,1.,*[r['score'] for r in validation],*[min(1.,r['score']+1e-7) for r in validation]})
 options=[]
 for threshold in candidates:
  metric=statistics([dict(r,predicted=int(r['score']>=threshold)) for r in validation])
  if metric['real_false_positive_rate']<=.05:options.append((metric['balanced_accuracy'],threshold,metric))
 _,threshold,val=max(options)
 report['calibrated']=dict(threshold=threshold,validation=val,test=statistics([dict(r,predicted=int(r['score']>=threshold)) for r in test]),protocol='First20 matched groups select threshold maximizing balanced accuracy with validation real FPR<=5%; remaining40 groups test. Not speaker-independent; cannot claim general business accuracy.')
 (ROOT/'reports/audio-mandarin-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report['metrics']);print('Baseline',report['baseline_metrics'])
if __name__=='__main__':main()
