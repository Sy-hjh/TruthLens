"""Reproduce validation-only threshold selection; never changes website release."""
import bootstrap,json
from check_recent_model import statistics
def main():
 root=bootstrap.ROOT
 rows=json.loads((root/'reports/smaug-whole-check.json').read_text(encoding='utf-8'))['whole_image_val']['results']
 best=None
 for i in range(1,1000):
  threshold=i/1000
  metrics=statistics([dict(row,predicted=int(row['score']>=threshold)) for row in rows])
  if metrics['real_false_positive_rate']>.05:continue
  key=(metrics['balanced_accuracy'],-metrics['real_false_positive_rate'])
  if best is None or key>best[0]:best=(key,threshold,metrics)
 if best is None:raise RuntimeError('No candidate threshold meets validation FPR requirement')
 result=dict(threshold=best[1],validation=best[2],rule='Max validation balanced accuracy subject to real FPR <= 5%; no test scores used.')
 (root/'reports/smaug-calibration.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(result)
if __name__=='__main__':main()
