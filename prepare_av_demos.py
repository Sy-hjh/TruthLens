"""Restore actual author-public AV examples; no local dubbing or new cloning."""
import bootstrap,hashlib,json,shutil,subprocess
from pathlib import Path
import requests,imageio_ffmpeg
from bootstrap import ROOT
ITEMS=[dict(name='av-real',author_file='A',id='1j2J0RCSTEHkzR7k-i9UT03vc4Xy2yFDG',sha256='ecb90c4c50e5f46f546446af872dbac741f09956022e5e129d572b37237c0a0c',video_label='real',audio_label='real'),dict(name='av-fake',author_file='D',id='1TCKZAKhdgNJdze3njJHuOmOTaMf_XBld',sha256='3976daf429c30a59ae62902b290230debb98b54b6941b4a7b20df4496cd71a7b',video_label='fake',audio_label='cloned')]
def main():
 folder=ROOT/'data/demo';folder.mkdir(parents=True,exist_ok=True);rows=[]
 for item in ITEMS:
  target=folder/(item['name']+'.mp4');existing=ROOT/'data/av-author-samples'/(item['author_file']+'.mp4')
  if not target.exists():
   if existing.exists():shutil.copy2(existing,target)
   else:
    response=requests.get('https://drive.usercontent.google.com/download',params={'id':item['id'],'export':'download'},timeout=60);response.raise_for_status();assert response.headers.get('Content-Type','').startswith('video/');temporary=target.with_suffix('.part');temporary.write_bytes(response.content);temporary.replace(target)
  assert hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256'],'Author public example checksum mismatch'
  wav=folder/(item['name']+'.wav')
  subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-nostdin','-y','-v','error','-i',str(target),'-vn','-ac','1','-ar','16000','-c:a','pcm_s16le',str(wav)],check=True)
  rows.append(dict(item,source='https://sites.google.com/view/fakeavcelebdash-lab/',scope='Author public 2021 dataset examples, English. Not a modern universal accuracy test. Audio extracted from actual original MP4, not dubbed locally.',audio_sha256=hashlib.sha256(wav.read_bytes()).hexdigest()))
 (folder/'av-source.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print('Author AV pair verified; actual audio tracks restored')
if __name__=='__main__':main()
