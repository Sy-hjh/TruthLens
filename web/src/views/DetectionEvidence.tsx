import type {ModuleResult} from '../api';
type Point={label:string;score:number;threshold:number};
function Plot({title,points}:{title:string;points:Point[]}){
 const top=22,bottom=158,width=640,left=52,right=620;const y=(s:number)=>bottom-Math.max(0,Math.min(1,s))*(bottom-top);const x=(i:number)=>left+(right-left)*(i+.5)/points.length;
 return <section className="evidence-plot"><h4>{title}</h4><svg viewBox={`0 0 ${width} 210`} role="img" aria-label={title+'：模型分数和触发阈值'}>
 {[0,.5,1].map(v=><g key={v}><line x1={left} x2={right} y1={y(v)} y2={y(v)} stroke="#dce3df"/><text x={left-8} y={y(v)+4} textAnchor="end">{v.toFixed(1)}</text></g>)}
 {points.length>1&&<polyline points={points.map((p,i)=>`${x(i)},${y(p.score)}`).join(' ')} fill="none" stroke="#486d67" strokeWidth="2"/>}
 {points.map((p,i)=><g key={i}><line x1={x(i)-Math.min(30,240/points.length)} x2={x(i)+Math.min(30,240/points.length)} y1={y(p.threshold)} y2={y(p.threshold)} stroke="#a04e25" strokeDasharray="4 3" strokeWidth="2"/><circle cx={x(i)} cy={y(p.score)} r="4" fill={p.score>=p.threshold?'#b34b40':'#4c7a70'}><title>{p.label}；分数{p.score.toFixed(4)}；阈值{p.threshold}</title></circle>{points.length<=12&&<text x={x(i)} y={184} textAnchor="middle">{p.label}</text>}</g>)}
 <text x={left} y={204}>圆点：模型分数　虚线：该项提醒线（非真假概率）</text></svg>
 <details><summary>查看逐项数值</summary><div className="table-wrap"><table><thead><tr><th>采样位置 / 时间</th><th>模型分数</th><th>阈值</th></tr></thead><tbody>{points.map((p,i)=><tr key={i}><td>{p.label}</td><td>{p.score.toFixed(4)}</td><td>{p.threshold.toFixed(4)}</td></tr>)}</tbody></table></div></details></section>
}
export default function DetectionEvidence({kind,module:m}:{kind:string;module:ModuleResult}){
 if(m.status!=='completed')return <div className="evidence-panel"><h3>本项没有有效检测数据</h3><p>{m.note||'未完成检测，不能展示分数或得出结论。'}</p></div>;
 const threshold=m.threshold??.5;const primary=(m.segments||[]).filter(p=>p.source?.repo!=='eliya/forensics_0.3B_xlsr_wild_deepfake_classifier');const secondary=(m.segments||[]).filter(p=>p.source?.repo==='eliya/forensics_0.3B_xlsr_wild_deepfake_classifier');
 return <div className="evidence-panel"><h3>查看本次检测依据</h3><p>圆点是本次检测分数，虚线是提醒线。分数不能直接证明伪造。</p>
 {m.score!==undefined&&<dl className="evidence-numbers"><div><dt>检测分数</dt><dd>{m.score.toFixed(4)}</dd></div><div><dt>提醒线</dt><dd>{threshold.toFixed(4)}</dd></div>{m.sensitivity_threshold!==undefined&&<div><dt>复查起点</dt><dd>{m.sensitivity_threshold.toFixed(4)}</dd></div>}</dl>}
 {kind==='image'&&<><p>检查图片的三个视图后汇总。不同视图结果可能不同，不能据此定位修图位置。{m.sensitivity_threshold!==undefined&&` ${m.sensitivity_threshold}–${threshold}为不确定区间，不能认定合成。`}</p>{m.views?.length?<Plot title="图片三视图输出" points={m.views.map(v=>({...v,threshold}))}/>:<p>旧报告未保存视图分数，重新上传可查看；不补造历史数据。</p>}</>}
 {kind==='video'&&<p>按时间抽取画面检查，再汇总结果。未检查每一帧，也未检测口型同步。</p>}
 {kind==='video'&&(m.moments?.length?<Plot title="视频采样帧输出" points={m.moments.map(p=>({label:p.start.toFixed(1)+'秒',score:p.score,threshold}))}/>:<p>旧报告未保存逐帧分数，重新上传可查看。</p>)}
 {kind==='audio'&&<>{primary.length>0&&<Plot title="声音分段检查" points={primary.map(p=>({label:`${p.start.toFixed(1)}–${(p.end??p.start+8).toFixed(1)}秒`,score:p.score,threshold:p.threshold??.5}))}/>} {m.secondary_check&&<Plot title="第二个声音模型复查（中间5秒）" points={[{label:'中段复查',score:m.secondary_check.score,threshold:m.secondary_check.threshold}]}/>} {!m.secondary_check&&secondary.length>0&&<Plot title="补充声学模型输出" points={secondary.map(p=>({label:p.start.toFixed(1)+'秒',score:p.score,threshold:p.threshold??.7}))}/>}<p>分段检查声音，必要时由另一个模型复查。两个分数分别判断。</p></>}
 <details><summary>检测方法和版本</summary><p>{m.note}</p><p>版本：{m.source?.version||'此旧记录未登记版本'}</p></details></div>
}
