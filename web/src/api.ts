export interface Source { repo?: string; version?: string }
export interface Segment { start: number; score: number; signal?: string; source?: Source }
export interface ModuleResult { status: string; note?: string; score?: number; threshold?: number; source?: Source; segments?: Segment[]; map_png?: string; moments?: {start:number;score:number}[]; detector_scores?:Record<string,number> }
export interface Report { id:string; filename:string; created_at:string; summary:string; context?:string; sha256:string; modules:Record<string,ModuleResult>; transcript?:{text:string;note?:string;raw_text?:string}; phrases:{source?:string;context?:string;excerpt:string;category:string;note:string}[]; limitations:string[]; next_steps:string[] }
export interface Metric {n:number;real_count:number;fake_count:number;balanced_accuracy:number|null;real_false_positive_rate:number|null;fake_miss_rate:number|null}
export interface Evidence {experiments:{title:string;note:string;metrics:Metric;rejected:number}[];releases:Record<string,string>;warning:string}
export interface Advice {engine:string;summary:string;actions:string[];sources:{id:string;title:string;url:string;snippet?:string}[];trace:{tool:string;status:string}[];note?:string}
export async function api<T>(url:string,options:RequestInit={},timeout=20000):Promise<T>{
 const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),timeout);
 try {const response=await fetch(url,{...options,signal:options.signal||controller.signal});const data=await response.json();if(!response.ok)throw Error(typeof data.detail==='string'?data.detail:'请求未成功，请稍后重试');return data as T}
 catch(error){if(error instanceof TypeError)throw Error('没有连上亲安服务。请启动软件后再试。');if(error instanceof DOMException&&error.name==='AbortError')throw Error('等待时间较长，请稍后在核验记录中查看。');throw error}finally{clearTimeout(timer)}
}
export function downloadReport(report:Report){const url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=`亲安-${report.id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
