"""Bounded LangChain agent: plan, call read-only tools, ground output, fall back.

Trace exposes tool actions and validation outcomes, not hidden chain of thought.
No tool can access contacts, open arbitrary URLs, run code or change model verdicts.
"""
import json,time,uuid,logging,math
import re
from .knowledge import ACTIONS,SUMMARIES
from .rag import retrieve,manifest

def evidence_summary(report):
 modules={k:{n:v.get(n) for n in ('status','score','title','failure_stage')} for k,v in report.get('modules',{}).items() if isinstance(v,dict)}
 return dict(summary=report.get('summary'),modules=modules,content_assessment={k:report.get(k,{}).get('assessment',{}) for k in ('speech_analysis','chat_analysis')},warning='模型分数不等于诈骗概率；不据此确认身份。')

def report_facts(report,question):
 facts=[]
 for name,title in [('video','视频画面'),('audio','声音'),('image','整图生成'),('tamper','局部篡改')]:
  m=report.get('modules',{}).get(name)
  if not isinstance(m,dict) or m.get('status')=='disabled':continue
  if name=='tamper' and m.get('method')=='fused':
   if m.get('status')!='completed':facts.append('图片异常检查未完成。')
   elif m.get('regions'):facts.append(f"标出 {len(m['regions'])} 处异常，建议复核红框区域。")
   elif m.get('relevance') in {'irrelevant','unmatched','unavailable'}:facts.append('重绘响应未关联到任务关键信息，未计入风险。')
   else:facts.append('图片异常检查未标出明显区域。')
   continue
  values=[(s.get('score'),s.get('threshold',.5)) for s in m.get('segments',[])]
  if isinstance(m.get('score'),(int,float)):values.append((m['score'],m.get('threshold',.5)))
  valid=[(a,b) for a,b in values if isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isfinite(a) and math.isfinite(b)]
  if m.get('status')!='completed' or not valid:facts.append(title+'检查尚未得到有效结果，不能把它当成真实或安全的依据。')
  elif name=='tamper':
   if m.get('regions'):
    facts.append(f"标出 {len(m['regions'])} 处局部异常，请对照原图复核。异常也可能由普通编辑或压缩引起。")
   else:
    facts.append('发现局部篡改风险，请对照原图复核。模型分数无法区分普通编辑和 AI 编辑。' if any(a>=b for a,b in valid) else '局部检查未达到提醒线，仍可能漏检。')
  elif any(a>=b for a,b in valid):facts.append(title+'检测出现了合成线索；这不能证明联系你的人是谁，也不等于已经证实诈骗。')
  elif name=='image' and isinstance(m.get('sensitivity_threshold'),(int,float)) and any(a>=m['sensitivity_threshold'] for a,_ in valid):facts.append('照片检测处于不确定区间，建议结合原图和来源继续核实。')
  else:facts.append(title+'本次未检出明确合成线索；仍可能漏检，不能据此确认身份。')
 for key,title in [('chat_analysis','聊天内容'),('speech_analysis','说话内容')]:
  a=report.get(key,{}).get('assessment',{})
  if a.get('title'):facts.append(title+'：'+a['title']+'。')
 daf=report.get('modules',{}).get('daf',{})
 if daf.get('status')=='completed' and daf.get('regions'):
  fields='、'.join(dict.fromkeys(region['field'] for region in daf['regions']))
  facts.append(f'在{fields}标出需核查的文字编辑线索。')
 note='以下建议结合本次检测和检索到的公开资料。'
 if re.search(r'本人|身份|女儿|儿子|家人|谁|真人',question):note='合成检测不能核实说话人或画中人的身份。即使没检出合成，也请使用事先保存的号码确认。'
 elif re.search(r'概率|百分|多少|准确',question):note='这里的检测分数不是被骗概率，不能换算成你会不会被骗的百分比。'
 elif re.search(r'转账|付款|汇款|钱|验证码',question):note='先暂停付款或提供验证码，用另一条可信渠道核实要求。不要根据本报告直接决定转账。'
 return facts,note

def review(report,question,emit=None,use_model=True):
 from .advisor import validate_selection,extract_json
 started=time.monotonic();trace=[];seen={};called=[];run_id=uuid.uuid4().hex
 def event(tool,status,**extra):
  row=dict(tool=tool,status=status,elapsed_seconds=round(time.monotonic()-started,3),**extra);trace.append(row)
  if emit:emit(dict(type='step',run_id=run_id,**row))
 def search_tool(query):
  rows=retrieve(query)
  for row in rows:seen[row['id']]=row
  return rows
 query=(question+' '+str(report.get('context',''))+' '+str(report.get('transcript',{}).get('text',''))+' '+str(report.get('ocr',{}).get('text','')))[:1600]
 def grounded(value):
  if set(value)=={'summary_key','source_ids'}:
   refs=value['source_ids']
   if not isinstance(refs,list) or not 1<=len(refs)<=3 or any(not isinstance(i,str) or i not in seen for i in refs):raise ValueError('引用未经过实际检索')
   value=dict(value,action_ids=list(dict.fromkeys(seen[i]['action'] for i in refs)))
  return validate_selection(value,list(seen.values()))
 event('plan','准备读取报告、检索官方资料并验证建议来源')
 mode='retrieval_fallback';selection=None;agent_error=None
 if use_model:
  try:
   from langchain.agents import create_agent
   from langchain_core.tools import tool
   from .agent_model import LocalQwenTools
   @tool
   def read_report()->dict:
    """读取本次画面、声音等独立检测状态，不判断身份。应先调用。"""
    called.append('read_report');event('read_report','已读取独立检测状态');return evidence_summary(report)
   @tool
   def search_guidance(query:str)->list[dict]:
    """按本次问题检索官方反诈资料。query不超过1600字，可改写后重试。"""
    if not 1<=len(query)<=1600:raise ValueError('检索长度超限')
    rows=search_tool(query);called.append('search_guidance');event('search_guidance','混合检索完成',source_ids=[s['id'] for s in rows]);return rows
   @tool
   def read_source(source_id:str)->dict:
    """核对已检索来源的摘要和动作；只接受本次检索返回的source_id。"""
    if source_id not in seen:raise ValueError('来源没有经过本次检索')
    called.append('read_source');event('read_source','已核对资料来源',source_ids=[source_id]);return seen[source_id]
   agent=create_agent(model=LocalQwenTools(),tools=[read_report,search_guidance,read_source],system_prompt='你只能使用本次报告与只读资料工具。先read_report，再search_guidance，必要时read_source。请自主制定检索query，给出有引用的允许动作。不执行任何外部操作。')
   result=agent.invoke({'messages':[{'role':'user','content':json.dumps({'question':question,'untrusted_material_excerpt':query},ensure_ascii=False)}]},config={'recursion_limit':12})
   if not {'read_report','search_guidance'}<=set(called):raise ValueError('Agent skipped required evidence tools')
   try:selection=grounded(extract_json(result['messages'][-1].content))
   except ValueError:
    event('repair','引用或动作对应未通过，请模型依据实际来源修正一次')
    allowed=[dict(source_id=s['id'],action=s['action']) for s in seen.values()]
    correction='上一份结果未通过引用校验。请只输出summary_key和source_ids两个字段，选择下面的实际来源，不输出action_ids。无需重复读取报告。允许来源：'+json.dumps(allowed,ensure_ascii=False)
    result=agent.invoke({'messages':[*result['messages'],{'role':'user','content':correction}]},config={'recursion_limit':12})
    selection=grounded(extract_json(result['messages'][-1].content))
   mode='langchain_agent';event('output_guard','动作、引用及来源对应校验通过')
  except Exception as exc:
   logging.exception('LangChain review rejected; using grounded fallback')
   agent_error=type(exc).__name__;event('output_guard','Agent未完成或输出未通过校验，使用有来源兜底',error_type=agent_error)
 if selection is None:
  rows=search_tool(query)
  # Unknown-topic input receives general verification guidance explicitly, not invented sources.
  if not rows:rows=search_tool('亲友 视频 核实 来源')
  event('fallback_retrieval','检索兜底完成',source_ids=[s['id'] for s in rows])
  selection=dict(summary_key='inconclusive',action_ids=list(dict.fromkeys(s['action'] for s in rows)),source_ids=[s['id'] for s in rows])
  validate_selection(selection,rows)
 sources=[seen[s] for s in selection['source_ids']]
 actions=[ACTIONS[a] for a in dict.fromkeys(['pause',*selection['action_ids'],'callback'])]
 result=dict(engine='LangChain create_agent + 本地Qwen + 混合RAG' if mode=='langchain_agent' else '本地资料检索兜底',summary=SUMMARIES[selection['summary_key']],actions=actions,sources=sources,trace=trace,note='建议来自公开资料。请用自己保存的号码联系本人。',mode=mode,run_id=run_id,selection=selection,corpus=manifest(),duration_seconds=round(time.monotonic()-started,3),agent_error=agent_error,safety=dict(identity_verdict=False,payment_execution=False,contacts_access=False,raw_media_access=False))
 result['report_facts'],result['question_note']=report_facts(report,question)
 event('complete','核实建议已生成')
 from .agent_store import save_audit
 save_audit(report.get('id'),result)
 return result
