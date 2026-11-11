"""Restore the reviewed release on a fresh machine; never downloads training corpora."""
import bootstrap,json,hashlib,shutil,subprocess,sys,argparse
ROOT=bootstrap.ROOT

def main():
 p=argparse.ArgumentParser();p.add_argument('--skip-downloads',action='store_true');args=p.parse_args();release=json.loads((ROOT/'release/release.json').read_text(encoding='utf-8'))
 if not args.skip_downloads:
  for kind in ('video','image','asr_zh'):subprocess.run([sys.executable,'download_models.py',kind],cwd=ROOT,check=True)
  source=release['sources']['face-detector'];folder=ROOT/'models/face-detector';folder.mkdir(exist_ok=True)
  from collect_domain_cases import get
  data=get(f"https://media.githubusercontent.com/media/{source['repo']}/{source['revision']}/models/face_detection_yunet/face_detection_yunet_2023mar.onnx").content
  if hashlib.sha256(data).hexdigest()!=source['sha256']:raise RuntimeError('Face locator hash mismatch')
  (folder/'model.onnx').write_bytes(data);(folder/'source.json').write_text(json.dumps(source,indent=2),encoding='utf-8')
  advisor=ROOT/'models/advisor';advisor.mkdir(exist_ok=True);(advisor/'source.json').write_text(json.dumps(release['sources']['advisor'],indent=2),encoding='utf-8')
  for script in ('install_gend.py','install_audio_forensics.py'):subprocess.run([sys.executable,script],cwd=ROOT,check=True)
  if release.get('image',{}).get('engine')=='smaug':
   for script in ('install_modern_image_runtime.py','install_smaug.py'):subprocess.run([sys.executable,script],cwd=ROOT,check=True)
  for item in release.get('demo_videos',[]):
   path=ROOT/'data/demo'/(item['name']+'.mp4');path.parent.mkdir(parents=True,exist_ok=True);blob=get(f"https://huggingface.co/datasets/{item['source_repo']}/resolve/{item['revision']}/{item['source_path']}").content
   if hashlib.sha256(blob).hexdigest()!=item['sha256']:raise RuntimeError('Demo hash mismatch')
   path.write_bytes(blob)
 video=release['video']
 if video.get('engine')=='video-fusion':
  head=ROOT/video['head'];head.parent.mkdir(parents=True,exist_ok=True);original=ROOT/'release/video-head.pt'
  if hashlib.sha256(original.read_bytes()).hexdigest()!=video['head_sha256']:raise RuntimeError('Packaged head hash mismatch')
  shutil.copyfile(original,head)
 for kind in ('video','audio','image'):
  if kind not in release:continue
  target=ROOT/'models'/('active-'+kind+'.json');temp=target.with_suffix('.tmp');temp.write_text(json.dumps(release[kind],ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(target)
 print('Reviewed release restored. Start with start-background.cmd')
if __name__=='__main__':main()
