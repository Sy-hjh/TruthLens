"""Single private local worker; model cached on CPU, no waveform/result caching."""
import atexit,json,os,queue,subprocess,sys,threading,uuid,time
from bootstrap import ROOT
_worker=None
_queue=None
_signature=None
_log=None

def close():
 global _worker,_log
 if _worker is not None:
  try:
   if _worker.stdin:_worker.stdin.close()
   _worker.wait(timeout=2)
  except Exception:
   _worker.terminate()
   try:_worker.wait(timeout=2)
   except Exception:_worker.kill()
  _worker=None
 if _log is not None:_log.close();_log=None
atexit.register(close)

def signature():
 source=ROOT/'models/verispoof/source.json';meta=json.loads(source.read_text(encoding='utf-8'))
 paths=[source,ROOT/'backend/verispoof_worker.py']+[ROOT/'models/verispoof'/name for name in meta['sha256']]
 return tuple((str(p),p.stat().st_size,p.stat().st_mtime_ns) for p in paths)

def predict(path,timeout=180):
 global _worker,_queue,_signature,_log
 start=time.monotonic();current=signature();cold=_worker is None or _worker.poll() is not None or _signature!=current
 if cold:
  close();_queue=queue.Queue();responses=_queue
  env=dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONUTF8='1',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2',OPENBLAS_NUM_THREADS='1')
  _log=(ROOT/'runtime/acoustic-worker.log').open('a',encoding='utf-8')
  _worker=subprocess.Popen([sys.executable,str(ROOT/'backend/verispoof_worker.py'),'--serve'],cwd=ROOT,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=_log,text=True,encoding='utf-8',bufsize=1)
  process=_worker
  def read():
   try:
    for line in process.stdout:
     try:responses.put(json.loads(line))
     except ValueError:continue
   finally:responses.put({'closed':True})
  threading.Thread(target=read,daemon=True).start()
  try:
   ready=responses.get(timeout=120)
   if not ready.get('ready'):raise RuntimeError('声音模型加载失败，请查看运行日志；不是无音轨。')
  except queue.Empty:
   close();raise TimeoutError('声音模型加载超时；不是无音轨。')
  _signature=current
 ident=uuid.uuid4().hex
 try:
  _worker.stdin.write(json.dumps({'id':ident,'path':str(path)})+'\n');_worker.stdin.flush();result=_queue.get(timeout=timeout)
  if result.get('id')!=ident:raise RuntimeError('声音模型进程异常退出；音轨已提取。')
  if 'error' in result:raise RuntimeError('声音模型推理失败：'+result['error'])
  result.update(cold_start=cold,total_seconds=time.monotonic()-start);return result
 except queue.Empty:
  close();raise TimeoutError('声音模型推理超时；音轨存在，可查看独立转写结果。')
 except (OSError,RuntimeError):
  close();raise
