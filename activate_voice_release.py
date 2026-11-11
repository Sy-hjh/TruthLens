"""Promote the reviewed acoustic-only release; preserve the previous config."""
import bootstrap,json
from bootstrap import ROOT

def main():
 path=ROOT/'models/active-audio.json';old=json.loads(path.read_text(encoding='utf-8'))
 if old.get('engine')=='verispoof':
  print('Reviewed native acoustic release already active; no configuration changed.');return
 backup=path.with_name('audio-before-verispoof.json')
 if not backup.exists():backup.write_text(json.dumps(old,indent=2),encoding='utf-8')
 secondary=json.loads(backup.read_text());secondary.update(threshold=.70,version='xlsr-aasist-secondary-070-20261111')
 info=dict(approved=True,engine='verispoof',version='qinan-acoustic-cascade-r1-20261111',threshold=.5,primary=dict(repo='AustinXiao/VeriSpoof-Plus',revision='ef5b12112da17e0949b5e19fe0f9f198c9570fd9',manifest='models/verispoof/source.json',window_seconds=8,step_seconds=4),secondary=secondary,evidence='reports/voice-cascade-check.json',primary_holdout='reports/verispoof-test-channels.json',scope='Waveform only. Primary fixed protocol tested on 624 recordings / 6 held-out speakers; cascade is observed-set follow-up, not a new independent test. Unknown upstream overlap; only 32 genuine holdout recordings. Not universal clone detection or identity verification.')
 path.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
 release_path=ROOT/'release/release.json';release=json.loads(release_path.read_text(encoding='utf-8'));release['audio']=info
 release['sources']['verispoof']=dict(repo=info['primary']['repo'],revision=info['primary']['revision'],license='CC-BY-NC-4.0 weights; Apache-2.0 code',purpose='Native acoustic synthesis detection, no speech transcription')
 release_path.write_text(json.dumps(release,ensure_ascii=False,indent=2),encoding='utf-8')
 print(info['version'])
if __name__=='__main__':main()
