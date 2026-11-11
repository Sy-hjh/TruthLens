"""Reproduce the historical temporal experiment in isolated runtime folders.
Downloads official sources/weights; does not activate a website model.
"""
import bootstrap,requests,json,hashlib,sys,subprocess
from concurrent.futures import ThreadPoolExecutor
from range_stream import RangeStream
ROOT=bootstrap.ROOT;REPO='yinglinzheng/FTCN';COMMIT='853256a888bd5c4879955c06a4c5a666740f91a4';EXPECTED='3d08fc78174bbfdb3fbede317b95dcac9095202ed7113649eecf6e2ef5ee77d8'
def main():
 tree=requests.get(f'https://api.github.com/repos/{REPO}/git/trees/{COMMIT}?recursive=1',timeout=30);tree.raise_for_status();files=tree.json()['tree']
 selected=[r for r in files if r['type']=='blob' and r['path'].endswith(('.py','.yaml','.md','.txt')) and (r['path'].startswith(('model/','slowfast/','setting/')) or r['path'] in ['config.py','root_setting.yaml','test_on_raw_video.py','README.md','LICENSE','requirements.txt'])]
 def download(row):
  path=ROOT/'runtime/ftcn-source'/row['path'];path.parent.mkdir(parents=True,exist_ok=True)
  def valid(data):return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['sha']
  if path.exists() and valid(path.read_bytes()):return
  response=requests.get(f'https://raw.githubusercontent.com/{REPO}/{COMMIT}/{row["path"]}',timeout=40);response.raise_for_status();assert valid(response.content),'Source Git blob mismatch';path.write_bytes(response.content)
 with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(download,selected))
 folder=ROOT/'models/ftcn';folder.mkdir(exist_ok=True);path=folder/'author-weights.pth';url=f'https://github.com/{REPO}/releases/download/weights/ftcn_tt.pth'
 if not path.exists():
  temp=folder/'author-weights.part';offset=temp.stat().st_size if temp.exists() else 0;size=59248500
  response=requests.get(url,headers={'Range':'bytes=0-0'},stream=True,timeout=30);response.raise_for_status();cdn=response.url;response.close()
  with RangeStream(cdn,size,workers=10,start=offset) as stream,temp.open('ab') as out:
   while block:=stream.read(4*1024*1024):out.write(block);out.flush();print(out.tell(),'/',size,flush=True)
  if hashlib.sha256(temp.read_bytes()).hexdigest()!=EXPECTED:raise RuntimeError('Weight checksum mismatch; file retained for inspection')
  temp.replace(path)
 assert hashlib.sha256(path.read_bytes()).hexdigest()==EXPECTED,'Existing weight checksum mismatch'
 (folder/'source.json').write_text(json.dumps(dict(repo=REPO,commit=COMMIT,url=url,sha256=EXPECTED,year=2021,purpose='Historical research baseline, not SOTA or active website model'),indent=2),encoding='utf-8')
 subprocess.run([sys.executable,'-m','pip','install','--target',str(ROOT/'runtime/ftcn-packages'),'--no-deps','fvcore==0.1.5.post20221221','iopath==0.1.10','simplejson==4.3.0','portalocker==4.4.2','termcolor==3.3.0','tabulate==0.10.0'],check=True)
 print('Ready. Run: python evaluate_ftcn_candidate.py. No website model changed.')
if __name__=='__main__':main()
