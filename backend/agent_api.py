"""Additive API only: existing frontend and media APIs stay unchanged."""
import json,queue,threading
from fastapi import APIRouter,HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel,Field
from typing import Literal
from . import storage

router=APIRouter()
_slots=threading.BoundedSemaphore(1)

class ReviewRequest(BaseModel):
 question:str=Field(default='这份材料有哪些线索，我应该怎么核实？',min_length=1,max_length=200)

class FeedbackRequest(BaseModel):
 verdict:Literal['useful','not_useful','false_alarm','missed_risk']

@router.get('/api/agent/capabilities')
def capabilities():
 from importlib.metadata import version,PackageNotFoundError
 packages={}
 for name in ('langchain','langchain-core','langgraph'):
  try:packages[name]=version(name)
  except PackageNotFoundError:packages[name]=None
 from .rag import manifest
 return dict(framework=packages,tools=['read_report','search_guidance','read_source'],tool_protocol='LangChain tool calling (Function Calling)',max_tool_calls=4,recursion_limit=12,corpus=manifest(),local_only=True,frontend_changed=False,limitations=['不确认对方身份','不生成诈骗概率','不执行拨号或转账','流式事件仅提供执行进度，不公开模型隐含思考'])

@router.post('/api/cases/{key}/agent-review')
def review(key:str,body:ReviewRequest):
 report=storage.get(key)
 if not report:raise HTTPException(404,'报告不存在')
 if not _slots.acquire(blocking=False):raise HTTPException(429,'已有建议生成任务，请稍后重试')
 try:
  from .agent_review import review
  return review(report,body.question)
 finally:_slots.release()

@router.post('/api/cases/{key}/agent-events')
def stream(key:str,body:ReviewRequest):
 report=storage.get(key)
 if not report:raise HTTPException(404,'报告不存在')
 if not _slots.acquire(blocking=False):raise HTTPException(429,'已有建议生成任务，请稍后重试')
 events=queue.Queue(maxsize=32)
 def work():
  try:
   from .agent_review import review
   result=review(report,body.question,emit=events.put);events.put({'type':'result','result':result})
  except Exception:events.put({'type':'error','message':'建议生成失败，请保留独立核实这一步。'})
  finally:events.put(None);_slots.release()
 threading.Thread(target=work,daemon=True,name='qinan-agent-review').start()
 def frames():
  while True:
   try:item=events.get(timeout=10)
   except queue.Empty:yield ': keep-alive\n\n';continue
   if item is None:break
   yield 'data: '+json.dumps(item,ensure_ascii=False)+'\n\n'
 return StreamingResponse(frames(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@router.post('/api/cases/{key}/feedback')
def feedback(key:str,body:FeedbackRequest):
 if not storage.get(key):raise HTTPException(404,'报告不存在')
 from .agent_store import feedback
 return feedback(key,body.verdict)

@router.get('/api/agent/metrics')
def metrics():
 from .agent_store import stats
 return stats()
