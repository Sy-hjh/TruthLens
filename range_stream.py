"""Bounded parallel HTTP ranges exposed as a forward-only file."""
from concurrent.futures import ThreadPoolExecutor
import requests,time,io
class RangeStream(io.RawIOBase):
    def __init__(self,url,size,step=4*1024*1024,workers=16,start=0):
        if not 0<=start<=size:raise ValueError('Invalid resume offset')
        self.url=url;self.size=size;self.step=step;self.position=start;self.buffer=b'';self.index=start
        self.pool=ThreadPoolExecutor(max_workers=workers);self.pending={};self.next_start=start;self.workers=workers
        self.fill()
    def piece(self,start):
        end=min(self.size,start+self.step)-1
        for attempt in range(6):
            try:
                r=requests.get(self.url,headers={'Range':f'bytes={start}-{end}'},timeout=(30,90));r.raise_for_status()
                if r.status_code!=206 or len(r.content)!=end-start+1:raise ValueError('Server did not honor range')
                return r.content
            except (requests.RequestException,ValueError):
                if attempt==5:raise
                time.sleep(1)
    def fill(self):
        while len(self.pending)<self.workers and self.next_start<self.size:
            start=self.next_start;self.pending[start]=self.pool.submit(self.piece,start);self.next_start+=self.step
    def read(self,n=-1):
        if n<0:raise ValueError('Unbounded reads disabled')
        result=bytearray()
        while len(result)<n:
            if not self.buffer:
                if self.index>=self.size:break
                self.buffer=self.pending.pop(self.index).result();self.index+=self.step;self.fill()
            count=min(n-len(result),len(self.buffer));result.extend(self.buffer[:count]);self.buffer=self.buffer[count:];self.position+=count
        return bytes(result)
    def close(self):
        self.pool.shutdown(wait=True,cancel_futures=True);super().close()
