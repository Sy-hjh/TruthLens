"""Publish aggregate-only research results, including unsuccessful candidates."""
import bootstrap,json
from bootstrap import ROOT
def main():
 read=lambda name:json.loads((ROOT/'reports'/name).read_text(encoding='utf-8'))
 image=read('smaug-upgrade-comparison.json');candidate=read('omniaid-upgrade-comparison.json');video=read('spatiotemporal-upgrade-test.json')
 report=dict(smaug_mirage=image['metrics']['mirage_test'],omniaid_mirage=candidate['metrics']['mirage_test'],gend_fresh60=video['spatial_same_usable'],fakestormer_fresh60=video['temporal_author_threshold'],fusion_fresh60=video['metrics'],note='Mirage240 test-only; no local fitting. Video20 new source groups. Author/pretraining overlap unknown. Face swaps are not all generated video. Failed candidates remain visible; no automatic release.')
 path=ROOT/'reports/ordered-temporal-head-test.json'
 if path.exists():
  value=read(path.name);report['ordered_head_fresh60']=value['metrics'];report['ordered_head_baseline']=value['same_frames_baseline'];report['ordered_head_coverage']=value['coverage']
  baseline=ROOT/'reports/ordered-head-active-baseline.json'
  if baseline.exists():report['ordered_head_active_baseline']=read(baseline.name)['metrics']
 (ROOT/'reports/new-model-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report)
if __name__=='__main__':main()
