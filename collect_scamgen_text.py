"""Read only author-published text members over HTTP ranges; never execute archive code."""
import bootstrap,requests,json,io,zipfile,hashlib
ROOT=bootstrap.ROOT
class Remote(io.RawIOBase):
 def __init__(self,url,size):self.url=url;self.size=size;self.pos=0
 def seekable(self):return True
 def readable(self):return True
 def tell(self):return self.pos
 def seek(self,offset,whence=0):self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.size+offset;return self.pos
 def read(self,n=-1):
  if n<0:n=self.size-self.pos
  if not n:return b''
  if n>25*1024*1024:raise ValueError('Archive member exceeds text limit')
  r=requests.get(self.url,headers={'Range':f'bytes={self.pos}-{min(self.size,self.pos+n)-1}'},timeout=(10,60));r.raise_for_status()
  if r.status_code!=206:raise RuntimeError('Server did not honor bounded byte ranges')
  data=r.content;self.pos+=len(data);return data
def main():
 folder=ROOT/'data/text-fraud/scamgen';folder.mkdir(exist_ok=True)
 response=requests.get('https://data.mendeley.com/public-api/datasets/dkypjhkmgb/files',params={'folder_id':'root','version':1,'$start':0,'$limit':1000},headers={'Accept':'application/vnd.mendeley-public-dataset.1+json'},timeout=30);response.raise_for_status();meta=response.json()[0]
 p=requests.get(meta['content_details']['download_url'],headers={'Range':'bytes=-65536'},stream=True,timeout=30);p.raise_for_status();cdn=p.url;p.close();files=[]
 with zipfile.ZipFile(Remote(cdn,meta['size'])) as z:
  targets=[i for i in z.infolist() if ('/Data/Seed/' in i.filename and i.filename.rsplit('/',1)[-1] in ['ori_seed.csv','ori_seed_new.csv','ori_seed_5.txt','whowhywhat_coarse.txt']) or '/Data/D_Datasest_v5/1.datasetv1/Hard_' in i.filename or i.filename=='Telescam-and-fraud-intent-detection/README.md']
  for item in targets:
   target=folder/item.filename.rsplit('/',1)[-1]
   if not target.exists():target.write_bytes(z.read(item)) # zipfile checks member CRC.
   files.append(dict(member=item.filename,bytes=target.stat().st_size,crc32=item.CRC,sha256=hashlib.sha256(target.read_bytes()).hexdigest()));print(target.name,target.stat().st_size,flush=True)
 (folder/'source.json').write_text(json.dumps(dict(doi='10.17632/dkypjhkmgb.1',url='https://data.mendeley.com/datasets/dkypjhkmgb/1',license='CC-BY-4.0 plus any third-party terms',archive_expected_sha256=meta['content_details']['sha256_hash'],archive_whole_downloaded=False,verification='Official TLS + ZIP central directory/member CRC + local SHA; entire archive hash not verified for range-selected extraction.',files=files),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
