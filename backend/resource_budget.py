"""Shed only THIS application's idle model caches; never terminate user training."""
import gc,logging
from .text_runtime import free_memory
RESERVE=6*1024**3

def prepare():
    before=free_memory()
    if before>=RESERVE:return dict(trimmed=False,free_mb=round(before/1024**2))
    from .detector import lock
    if not lock.acquire(blocking=False):return dict(trimmed=False,reason='model_in_use')
    try:
        from .acoustic_worker_client import close
        from .text_runtime import drop_cache
        close();drop_cache();gc.collect()
        after=free_memory()
        logging.info('Released own idle caches: available RAM %.2f -> %.2f GB',before/1024**3,after/1024**3)
        return dict(trimmed=True,before_mb=round(before/1024**2),after_mb=round(after/1024**2))
    finally:lock.release()
