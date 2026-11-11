"""Export aggregate evidence only; exclude media rows, private cases and file locations."""
import bootstrap,json,hashlib
ROOT=bootstrap.ROOT
def clean(value):
 if isinstance(value,dict):
  return {k:len(v) if k=='rejected' and isinstance(v,list) else clean(v) for k,v in value.items() if k not in ('results','rows','checks')}
 if isinstance(value,list):return [clean(v) for v in value]
 return value
def main():
 p=ROOT/'docs/benchmarks.json';data=json.loads(p.read_text(encoding='utf-8'))
 for name in ['gend-check.json','gend-final.json','bfree-check.json','detectra-check.json','smaug-check.json','smaug-whole-check.json','smaug-whole-final.json','smaug-calibration.json','verispoof-val-channels.json','verispoof-test-channels.json','verispoof-phone-controls.json','voice-cascade-check.json','voice-head-validation.json','voice-data-audit.json','voice-resume-check.json','voice-selection.json','image-review-policy.json','chat-semantic-review.json','report-trace-check.json']:
  source=ROOT/'reports'/name;value=clean(json.loads(source.read_text(encoding='utf-8')));value['source_report_sha256']=hashlib.sha256(source.read_bytes()).hexdigest();data['reports'][name]=value
 data['generated']='2026-11-11';p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
