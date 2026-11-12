"""Prepare a gated ordered-video release; subsequent HTTP verification required."""
import bootstrap,json,hashlib,shutil
from bootstrap import ROOT
def main():
 read=lambda name:json.loads((ROOT/name).read_text(encoding='utf-8'))
 candidate=read('reports/ordered-temporal-head-test.json');baseline=read('reports/ordered-head-active-baseline.json');policy=read('models/video-ordered-head/promotion-policy.json')
 metric=candidate['metrics'];assert metric['balanced_accuracy']>baseline['metrics']['balanced_accuracy'] and metric['balanced_accuracy']>candidate['same_frames_baseline']['balanced_accuracy'];assert metric['false_positives']<=baseline['metrics']['false_positives'];assert candidate['coverage']>=baseline['coverage'];assert metric['n']==60
 frozen=read('models/video-ordered-head/frozen.json');data=read('models/video-ordered-head/data-protocol.json');assert hashlib.sha256((ROOT/'train_temporal_sequence.py').read_bytes()).hexdigest()==frozen['code_sha']
 shutil.copy2(ROOT/'models/video-ordered-head/best.pt',ROOT/'release/ordered-video-head.pt');protocol=dict(frozen,encoder_sha=data['encoder_sha'],sampler_sha=data['sampler_sha']);(ROOT/'release/ordered-video-protocol.json').write_text(json.dumps(protocol,indent=2),encoding='utf-8')
 path=ROOT/'models/active-video.json';old=read('models/active-video.json');backup=ROOT/'models/video-before-ordered.json'
 if old.get('engine')=='video-ordered-head':print('Already prepared; preserved previous config');return
 if not backup.exists():backup.write_text(json.dumps(old,indent=2),encoding='utf-8')
 info=dict(approved=True,engine='video-ordered-head',version='qinan-ordered-gru-r1-20261112',threshold=frozen['threshold'],head='release/ordered-video-head.pt',protocol='release/ordered-video-protocol.json',evaluation='reports/ordered-temporal-head-test.json',baseline='reports/ordered-head-active-baseline.json',scope='Frozen GenD encoder plus locally trained ordered four-frame bidirectional GRU. Not lip-sync, not all generated video. New20source60clip test, unknown actor/pretraining overlap.')
 path.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8');release=read('release/release.json');release['video']=info;(ROOT/'release/release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2),encoding='utf-8');print(info)
if __name__=='__main__':main()
