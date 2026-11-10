"""Recover valid updates and tolerate Windows antivirus/indexer file locks."""
import os,time,uuid
from pathlib import Path
import torch

def load_latest(checkpoint,device='cpu'):
    checkpoint=Path(checkpoint);candidates=[checkpoint,checkpoint.with_suffix('.tmp')]+list(checkpoint.parent.glob('last-recovery-*.pt'))
    valid=[]
    for path in candidates:
        if not path.exists():continue
        try:
            value=torch.load(path,map_location='cpu',weights_only=True)
            if not all(k in value for k in ('head','optimizer','step','epoch','cursor','manifest','base','batch_size')):continue
            valid.append(((value['step'],value['epoch'],value['cursor'],path.stat().st_mtime_ns),path,value))
        except (OSError,RuntimeError,EOFError,ValueError):continue
    if not valid:
        if any(p.exists() for p in candidates):raise RuntimeError('检查点存在但无法读取；请保留文件并排查，不会从零覆盖。')
        return None
    _,path,value=max(valid,key=lambda x:x[0])
    print(f'恢复检查点：{path.name}，更新次数={value["step"]}',flush=True)
    return value

def save_checkpoint(value,checkpoint):
    checkpoint=Path(checkpoint)
    temp=checkpoint.parent/('last-recovery-'+uuid.uuid4().hex+'.pt')
    with temp.open('wb') as stream:
        torch.save(value,stream);stream.flush();os.fsync(stream.fileno())
    for attempt in range(8):
        try:
            temp.replace(checkpoint);return checkpoint
        except PermissionError:
            if attempt<7:time.sleep(min(.1*2**attempt,1))
    print(f'主检查点被占用，最新进度已安全保存在{temp.name}；下次自动恢复。',flush=True)
    return temp

def acquire_training_lock(directory):
    import msvcrt
    handle=(Path(directory)/'training.lock').open('a+b')
    handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
    try:msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
    except OSError:
        handle.close();raise RuntimeError('这个输出目录已有训练进程，请勿重复启动。')
    return handle
