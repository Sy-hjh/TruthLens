"""Same acoustic protocol as the website; no transcript, filename, label or text input."""
import bootstrap,json,argparse,time
from verispoof_local import load
from voice_features import audio,variants
from backend.acoustic_protocol import analyze
from binary_metrics import statistics
def main():
 p=argparse.ArgumentParser();p.add_argument('--split',choices=['val','test'],default='val');a=p.parse_args();root=bootstrap.ROOT
 rows=[r for r in json.loads((root/'data/clone-bench/manifest-audited.json').read_text(encoding='utf-8')) if r['split']==a.split]
 if any(not (root/r['path']).exists() for r in rows):raise RuntimeError('Download and verify all evaluation samples first')
 model=load();output={name:[] for name in ['clean','aac32','phone8']};start=time.monotonic()
 for i,row in enumerate(rows):
  for name,signal in zip(output,variants(audio(root/row['path']))):
   parts=analyze(model,signal);score=max(x['score'] for x in parts);output[name].append(dict(row,score=score,predicted=int(score>=.5),segments=parts))
  if i%20==0:print('VeriSpoof',a.split,i+1,'/',len(rows),'seconds',round(time.monotonic()-start),flush=True)
 report={name:dict(metrics=statistics(results),by_generator={g:statistics([r for r in results if r['generator'] in (g,'human')]) for g in sorted({r['generator'] for r in results if r['label']==1})},results=results) for name,results in output.items()}
 report['protocol']=dict(window_seconds=8,step_seconds=4,clip_score='maximum window signal',native_threshold=0,input='waveform only, no speech transcript',upstream_overlap='unknown',split=a.split)
 path=root/f'reports/verispoof-{a.split}-channels.json';temp=path.with_suffix('.partial.json');temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
 for name in output:print(name,report[name]['metrics'],flush=True)
if __name__=='__main__':main()
