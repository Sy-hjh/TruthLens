import {Component,Suspense,lazy,useEffect,useState} from 'react';
import type {ReactNode} from 'react';
import {createRoot} from 'react-dom/client';
import {api} from './api';
import type {Report} from './api';
import Upload from './views/Upload';
import './style.css';
const Contacts=lazy(()=>import('./views/Contacts'));const Practice=lazy(()=>import('./views/Practice'));const History=lazy(()=>import('./views/History'));const ReportView=lazy(()=>import('./views/Report'));const Evidence=lazy(()=>import('./views/Evidence'));
type Page='check'|'contacts'|'practice'|'history'|'evidence'|'report';
class Boundary extends Component<{children:ReactNode},{failed:boolean}>{state={failed:false};static getDerivedStateFromError(){return{failed:true}}render(){return this.state.failed?<article className="card"><h2>页面暂时没能显示</h2><p>已保存的报告仍在。刷新后可到核验记录查看。</p><button onClick={()=>location.reload()}>重新打开</button></article>:this.props.children}}
function App(){
 const allowed:Page[]=['check','contacts','practice','history','evidence'];const fromHash=()=>allowed.includes(location.hash.slice(1) as Page)?location.hash.slice(1) as Page:'check';
 const [page,setPage]=useState<Page>(fromHash);const [report,setReport]=useState<Report|null>(null);const[health,setHealth]=useState('正在连接本机服务');
 useEffect(()=>{const handler=()=>setPage(fromHash());addEventListener('hashchange',handler);api<{models:Record<string,boolean>}>('/api/health').then(x=>setHealth(x.models.video&&x.models.audio?'本机模型已就绪':'部分模型尚未安装')).catch(e=>setHealth(e.message));return()=>removeEventListener('hashchange',handler)},[]);
 function go(next:Page){setPage(next);if(next!=='report')location.hash=next;window.scrollTo({top:0,behavior:'smooth'})}
 function open(r:Report){setReport(r);setPage('report');window.scrollTo(0,0)}
 const nav:[Page,string,string][]=[['check','检查收到的材料','◎'],['contacts','联系我的家人','♡'],['practice','练习识别骗局','▧'],['history','查看核验记录','◷']];
 return <><aside className="sidebar"><a className="brand" href="#check" onClick={()=>go('check')}><span className="brand-mark">安</span><span>亲安<small>QINAN · 先核实，再放心</small></span></a><p className="side-label">老人自己的反诈帮手</p><nav aria-label="主要功能">{nav.map(([id,label,icon])=><button key={id} className={page===id?'nav active':'nav'} onClick={()=>go(id)}><span aria-hidden="true">{icon}</span>{label}</button>)}</nav><div className="side-bottom"><span className="privacy-dot"/> 原始材料处理后删除<p>检测提供线索<br/>身份仍要独立核实</p><a href="#evidence" onClick={()=>go('evidence')}>实测结果与模型版本 ↗</a></div></aside><main><header className="topbar"><span>给关心的人，多一份安心</span><span className="connection"><i/>{health}</span></header><Boundary><Suspense fallback={<p className="loading" role="status">正在打开，请稍等…</p>}>{page==='check'?<Upload onComplete={open} onContacts={()=>go('contacts')}/>:page==='contacts'?<Contacts/>:page==='practice'?<Practice/>:page==='history'?<History onOpen={open}/>:page==='evidence'?<Evidence/>:report?<ReportView key={report.id} report={report} onContacts={()=>go('contacts')} onUpdate={setReport}/>:<p>请先检查一份材料。</p>}</Suspense></Boundary><footer><a href="#evidence" onClick={()=>go('evidence')}>亲安 · 查看实测与版本 ↗</a> <span>检测结果不能证明身份真实，也不直接判定诈骗</span></footer></main></>
}
createRoot(document.getElementById('root')!).render(<App/>);
