import {useState} from 'react';
import {api,downloadReport} from '../api';import type {Report} from '../api';
export default function ChatReport({report,onContacts,onUpdate}:{report:Report;onContacts:()=>void;onUpdate:(r:Report)=>void}){
 const[editing,setEditing]=useState(false),[text,setText]=useState(report.ocr?.text||''),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function save(){setBusy(true);setError('');try{const form=new FormData();form.append('text',text);onUpdate(await api('/api/cases/'+report.id+'/chat-text',{method:'POST',body:form},120000));setEditing(false)}catch(e){setError(e instanceof Error?e.message:'没有保存成功')}finally{setBusy(false)}}
 const signals=report.chat_analysis?.signals||[];
 return <><div className="report-top"><div><p className="eyebrow">聊天截图分析</p><h1>先看清对方提出了什么要求</h1><p>{report.filename}</p></div><div className="toolbar"><button onClick={()=>downloadReport(report)}>下载分析记录</button><button onClick={()=>window.print()}>打印</button></div></div>
 <article className="notice"><h2>{signals.length?'这些要求值得先核实':'先核对提取的聊天文字'}</h2><p>这里只分析聊天内容，不判断图片是否伪造，也不检测声音。</p></article>
 <article className="card"><h2>截图里的文字</h2>{editing?<><label className="field">按原截图修改<textarea rows={8} maxLength={4000} value={text} onChange={e=>setText(e.target.value)}/></label><button className="primary" disabled={busy||!text.trim()} onClick={save}>{busy?'正在重新分析…':'确认文字并重新分析'}</button></>:<><p className="transcript" style={{whiteSpace:'pre-wrap'}}>{report.ocr?.text}</p><button onClick={()=>setEditing(true)}>文字识别有误？修改</button></>}{error&&<p role="alert" className="error">{error}</p>}</article>
 <article className="card"><h2>结合原话看要求</h2>{signals.length?signals.map((s,i)=><div className="phrase" key={i}><h3>{s.title}</h3><blockquote>{s.quote}</blockquote></div>):<p>{report.chat_analysis?.status==='completed'?'这次没有提取出明确的操作要求；这不等于聊天安全。':'文字已提取，自动分析暂不可用，请人工核对。'}</p>}<p>出现借款、验证码或新账户等要求时，先用原来保存的号码联系本人。聊天中的一句称呼不能证明身份。</p><button className="primary" onClick={onContacts}>联系我的家人 ↗</button></article></>
}
