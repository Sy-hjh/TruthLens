"""Request a graceful stop; leaves all checkpoints and caches intact."""
import bootstrap
(bootstrap.ROOT/'runtime/STOP_OPTIMIZATION').touch()
print('已请求停止优化。正在进行的下载/特征批次可能需要完成；训练进度会保留。')
