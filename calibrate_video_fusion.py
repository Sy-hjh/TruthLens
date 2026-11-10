"""Two frozen video detectors; fit only a 2-input calibration layer on old validation groups."""
import bootstrap,json,numpy as np,torch
from pathlib import Path
from scipy.optimize import minimize
from check_recent_model import statistics
ROOT=bootstrap.ROOT

def logit(p):return np.log(np.clip(p,1e-5,1-1e-5)/(1-np.clip(p,1e-5,1-1e-5)))
def fusion(a,b,coef):return float(1/(1+np.exp(-np.clip(coef[0]*logit(a)+coef[1]*logit(b)+coef[2],-30,30))))
def main():
 calibration=json.loads((ROOT/'reports/sifta-calibration.json').read_text());rows=calibration['results'];head=torch.nn.Linear(768,2);head.load_state_dict(torch.load(ROOT/'models/video-face-adapt/best-head.pt',weights_only=True));head.eval();paired=[]
 for row in rows:
  feature=torch.load(ROOT/'runtime/video-features'/(row['sha256']+'-face-v1.pt'),weights_only=True)
  with torch.inference_mode():p=head(feature).softmax(-1)[0,1].item()
  paired.append(dict(row,videomae=p))
 x=np.array([[logit(r['score']),logit(r['videomae'])] for r in paired]);y=np.array([r['label'] for r in paired])
 def objective(c):
  z=x@c[:2]+c[2];return np.mean(np.logaddexp(0,z)-y*z)+.1*np.sum(c[:2]**2)
 fit=minimize(objective,np.array([.5,.5,0.]),bounds=[(0,None),(0,None),(None,None)],method='L-BFGS-B');assert fit.success
 coef=fit.x.tolist();r=[dict(a,score=fusion(a['score'],a['videomae'],coef),predicted=int(fusion(a['score'],a['videomae'],coef)>=.5)) for a in paired]
 report=dict(coefficients=coef,threshold=.5,calibration_fit_metrics=statistics(r),calibration_source_count=25,note='50 clips from previous validation source groups used to FIT the2-input calibration layer; fitted score is not independent validation. L2=.1, nonnegative detector coefficients, intercept free. Both video encoders frozen. New source test required.')
 left=json.loads((ROOT/'reports/sifta-diagnostic.json').read_text())['results'];right={r['sha256']:r for r in json.loads((ROOT/'reports/video-release-check.json').read_text())['results']};out=[]
 for a in left:
  if a['sha256'] not in right:continue
  p=fusion(a['score'],right[a['sha256']]['score'],coef);out.append(dict(a,score=p,predicted=int(p>=.5)))
 report['observed_diagnostic']=statistics(out);report['observed_results']=out
 (ROOT/'models/video-face-adapt/fusion-calibration.json').write_text(json.dumps(report,indent=2));(ROOT/'reports/video-fusion-calibration.json').write_text(json.dumps(report,indent=2));print('Frozen fusion calibration',coef,report['calibration_fit_metrics']);print('Observed diagnostic only',report['observed_diagnostic'])
if __name__=='__main__':main()
