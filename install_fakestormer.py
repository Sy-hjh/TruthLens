"""Download one actual author file, not Dropbox's non-resumable 2GB folder ZIP."""
import bootstrap,requests,re,html,json,hashlib,time
from urllib.parse import urlparse,parse_qsl,urlencode,urlunparse
from range_stream import RangeStream
ROOT=bootstrap.ROOT
FILENAME='TopDownDetector_C0_ViTBase224_ST_hm100_tempLOC0.2_4SBI_SAM_mp0.01_temp2_0vidAug_0.25_temp_normlms_IN_model_best.pth'
FOLDER='https://www.dropbox.com/scl/fo/elk2szqf0du4l6zm5job9/AAdVmNH--6ywHBZGNQJlR5o'
def main():
 folder=ROOT/'models/fakestormer';folder.mkdir(exist_ok=True);target=folder/'author-c0.pth'
 response=requests.get(FOLDER,params={'rlkey':'j8xesf2fu4ahxdw99w5ndrkb2','preview':FILENAME},timeout=(20,60));response.raise_for_status()
 match=re.search(r'<meta content="([^"]+)" name="al:web:url"',response.text);url=html.unescape(match.group(1));parsed=urlparse(url)
 if parsed.hostname!='www.dropbox.com' or FILENAME not in parsed.path:raise RuntimeError('Unexpected author file link')
 query=dict(parse_qsl(parsed.query));query['dl']='1';query['_']=str(time.time_ns());url=urlunparse(parsed._replace(query=urlencode(query)))
 probe=requests.get(url,headers={'Range':'bytes=0-0'},stream=True,timeout=(20,60));probe.raise_for_status();cdn=probe.url
 print('Author individual file',probe.status_code,probe.headers.get('Content-Range'),probe.headers.get('Content-Length'),flush=True)
 if probe.status_code!=206:probe.close();raise RuntimeError('Individual file does not support verified range resume')
 size=int(probe.headers['Content-Range'].split('/')[-1]);probe.close()
 if not 1_000_000<size<1_600_000_000:raise RuntimeError('Unexpected weight size')
 if not target.exists():
  partial=folder/'author-c0.part';offset=partial.stat().st_size if partial.exists() else 0
  # Dropbox's signed CDN URL may bind a Range: do not reuse a 0-0 redirect
  # for different ranges. Request the public author URL itself for each chunk.
  class AuthorStream(RangeStream):
   def piece(self,start):
    end=min(self.size,start+self.step)-1
    for attempt in range(5):
     try:
      r=requests.get(self.url+'&part='+str(start)+'&attempt='+str(time.time_ns()),headers={'Range':f'bytes={start}-{end}'},timeout=(20,90));r.raise_for_status()
      if r.status_code!=206 or len(r.content)!=end-start+1:raise RuntimeError('Author file range was not honored')
      return r.content
     except (requests.RequestException,RuntimeError):
      if attempt==4:raise
      time.sleep(1+attempt)
  with AuthorStream(url,size,workers=6,start=offset) as stream,partial.open('ab') as output:
   while block:=stream.read(4*1024*1024):output.write(block);output.flush();print(output.tell(),'/',size,flush=True)
  if partial.stat().st_size!=size:raise RuntimeError('Incomplete author weight')
  partial.replace(target)
 digest=hashlib.sha256(target.read_bytes()).hexdigest()
 (folder/'source.json').write_text(json.dumps(dict(repo='10Ring/FakeSTormer',commit='c5b5f75100b878212a192c00013275f275f86182',file=FILENAME,url=url,bytes=size,sha256=digest,license='SnT academic license, see author LICENSE',verification='Official author-linked Dropbox individual file, verified range length and locally recorded SHA256; author did not supply independent hash'),indent=2),encoding='utf-8');print('Downloaded author file',digest,flush=True)
if __name__=='__main__':main()
