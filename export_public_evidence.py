"""Export metrics without private media, transcripts, file paths or contact data."""
import bootstrap,json,hashlib
from pathlib import Path
ROOT=bootstrap.ROOT
METRIC_KEYS={'n','real_count','fake_count','false_positives','false_negatives','real_false_positive_rate','fake_miss_rate','balanced_accuracy','accuracy'}
def clean(value):
 if isinstance(value,dict):
  if 'balanced_accuracy' in value:return {k:v for k,v in value.items() if k in METRIC_KEYS}
  return {k:clean(v) for k,v in value.items() if k not in {'results','baseline','observed_results','selection','rejected','local_edit_results','predictor'} and (isinstance(v,dict) or k in METRIC_KEYS or k in {'planned','processed','coverage','threshold','temperature','weights_sha256'})}
 return value

def main():
 names=['balanced-test','domain-evaluation','domain-candidate','domain-mlp-candidate','video-diagnostic','video-face-adapt-test','video-release-check','integrity-v9-diagnostic','video-fusion-calibration','audio-mandarin-check','video-final-evaluation']
 reports={}
 for name in names:
  path=ROOT/'reports'/(name+'.json')
  if path.exists():reports[path.name]=dict(clean(json.loads(path.read_text(encoding='utf-8'))),source_report_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
 (ROOT/'docs/benchmarks.json').write_text(json.dumps(dict(generated='2026-11-11',note='Exported actual aggregate metrics; private cases and raw records excluded.',reports=reports),ensure_ascii=False,indent=2),encoding='utf-8')
 print('Public aggregate evidence exported',len(reports))
if __name__=='__main__':main()
