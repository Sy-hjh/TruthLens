"""Observed-set follow-up of a fixed waveform-only cascade; not a fresh final test."""
import bootstrap,json,argparse,torch,numpy as np
from backend.voice_forensics import load_model,waveform
from voice_features import audio,variants
from binary_metrics import statistics
def main():
 root=bootstrap.ROOT;torch.set_num_threads(2);model=load_model().to('cuda' if torch.cuda.is_available() else 'cpu');device=next(model.parameters()).device;out={}
 for split in ['val','test','phone']:
  source=json.loads((root/('reports/verispoof-phone-controls.json' if split=='phone' else f'reports/verispoof-{split}-channels.json')).read_text(encoding='utf-8'))
  groups={'clean':source} if split=='phone' else {k:source[k] for k in ['clean','aac32','phone8']}
  for channel,group in groups.items():
   rows=group['results'];results=[]
   for i,row in enumerate(rows):
    primary=row['predicted'];second=None
    if not primary:
     signal=audio(root/row['path']);signal=variants(signal)[['clean','aac32','phone8'].index(channel)] if channel!='clean' else signal
     with torch.inference_mode():second=1-model(waveform(signal).to(device)).sigmoid().item()
    predicted=int(primary or (second is not None and second>=.7));results.append(dict(row,primary_predicted=primary,secondary_score=second,secondary_threshold=.7,predicted=predicted))
   out[split+'_'+channel]=dict(metrics=statistics(results),results=results);print(split,channel,out[split+'_'+channel]['metrics'],flush=True)
 out['protocol']=dict(primary_threshold='author log-likelihood ratio >= 0',secondary_threshold=.7,rule='Only when primary has no positive window, run frozen XLS-R/AASIST on center5s; supplementary positive requires >= .70.',scope='Follow-up on already observed sets; not a new independent accuracy benchmark. No local fitting on test speaker recordings.')
 (root/'reports/voice-cascade-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
