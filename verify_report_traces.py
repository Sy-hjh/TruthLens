"""Verify that displayed traces reproduce actual aggregate outputs, without exporting private cases."""
import bootstrap,json,math,requests
ROOT=bootstrap.ROOT
def main():
 base='http://127.0.0.1:8010';rows=requests.get(base+'/api/cases',timeout=10).json();images=[];audio=False
 for entry in rows[:60]:
  report=requests.get(base+'/api/cases/'+entry['id'],timeout=10).json();modules=report.get('modules',{});im=modules.get('image',{})
  if im.get('views'):
   assert len(im['views'])==3
   expected=1/(1+math.exp(-sum(v['logit'] for v in im['views'])/3))
   assert abs(expected-im['score'])<1e-6
   images.append(dict(points=3,aggregation_reproduced=True))
  sound=modules.get('audio',{})
  if sound.get('analysis_basis')=='acoustic_waveform_only':
   for part in sound['segments']:assert 0<=part['score']<=1 and 0<=part['start']<part['end']<=sound['analyzed_seconds']+.001
   audio=True
 video=json.loads((ROOT/'reports/deployment-http.json').read_text(encoding='utf-8'))['video'];points=video['moments'];assert 1<=len(points)<=8
 assert abs(sum(p['score'] for p in points)/len(points)-video['score'])<1e-7
 assert images and audio
 out=dict(scope='Trace consistency, not detection accuracy; no private filenames or media exported.',image_reports_checked=len(images),image_mean_logits_match=True,video_points=len(points),video_mean_matches=True,audio_time_ranges_valid=True)
 (ROOT/'reports/report-trace-check.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(out)
if __name__=='__main__':main()
