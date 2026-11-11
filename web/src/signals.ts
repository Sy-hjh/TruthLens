import type {ModuleResult} from './api';
export type SignalLevel='alert'|'uncertain'|'unavailable';
export function moduleSignal(m:ModuleResult){
 const values=m.segments?.map(s=>({score:s.score,threshold:s.threshold??.5,start:s.start}))||[];
 if(m.score!==undefined)values.push({score:m.score,threshold:m.threshold??.5,start:0});
 if(m.status!=='completed'||!values.length)return{level:'unavailable' as SignalLevel,title:'这一项暂时无法判断',score:null,flagged:0,total:0};
 const flagged=values.filter(v=>v.score>=v.threshold).length;const score=Math.max(...values.map(v=>v.score));
 return{level:(flagged?'alert':'uncertain') as SignalLevel,title:flagged?'发现合成线索':'还不能确认真假',score,flagged,total:values.length};
}
