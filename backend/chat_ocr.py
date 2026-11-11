"""Local PP-OCRv6 for an explicitly selected chat screenshot, not audio transcription."""
import sys,threading,json,hashlib
import numpy as np
from bootstrap import ROOT
_engine=None;_lock=threading.Lock()
def available():return (ROOT/'runtime/ocr-packages/rapidocr/models/PP-OCRv6_rec_small.onnx').is_file()
def read(image):
 global _engine
 sys.path.insert(0,str(ROOT/'runtime/ocr-packages')) if str(ROOT/'runtime/ocr-packages') not in sys.path else None
 from rapidocr import RapidOCR
 path=ROOT/'runtime/ocr-packages/rapidocr/models'
 with _lock:
  if _engine is None:
   source=json.loads((ROOT/'models/chat-ocr/source.json').read_text())
   for name,expected in source['sha256'].items():
    if hashlib.sha256((path/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('截图文字模型校验失败')
   _engine=RapidOCR(params={'Det.model_path':str(path/'PP-OCRv6_det_small.onnx'),'Rec.model_path':str(path/'PP-OCRv6_rec_small.onnx'),'Cls.model_path':str(path/'ch_ppocr_mobile_v2.0_cls_mobile.onnx'),'Global.log_level':'error'})
  output=_engine(np.array(image.convert('RGB')))
 rows=[dict(text=str(text),confidence=float(confidence),box=box.tolist()) for text,confidence,box in zip(output.txts or [],output.scores or [],output.boxes if output.boxes is not None else [])]
 text='\n'.join(x['text'] for x in rows)
 if not text.strip():raise ValueError('没有读到清晰文字，请上传清晰的聊天截图。')
 return dict(status='completed',text=text[:4000],lines=rows,source=dict(repo='RapidAI/RapidOCR',version='3.10.0 / PP-OCRv6'),note='仅提取截图文字，不判断截图是否伪造；请先核对识别结果。')
