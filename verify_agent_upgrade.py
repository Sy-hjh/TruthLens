"""Reproducible retrieval ablation and optional REAL local LangChain model runs."""
import bootstrap,json,argparse,time,tempfile
from pathlib import Path
from unittest.mock import patch
from backend.rag import retrieve,manifest
from backend.knowledge import search

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
 cases=json.loads((bootstrap.ROOT/'docs/rag-eval-cases.json').read_text(encoding='utf-8'))
 results=[]
 for c in cases['cases']:
  old=search(c['query']);new=retrieve(c['query']);rel=set(c['relevant_ids'])
  results.append(dict(query=c['query'],expected=sorted(rel),baseline_ids=[d['id'] for d in old],hybrid_ids=[d['id'] for d in new],baseline_hit=any(d['id'] in rel for d in old),hybrid_hit=any(d['id'] in rel for d in new)))
 out=dict(scope=cases['scope'],corpus=manifest(),retrieval=dict(n=len(results),baseline_hits=sum(x['baseline_hit'] for x in results),hybrid_hits=sum(x['hybrid_hit'] for x in results),rows=results),live=[])
 if args.live:
  from backend.agent_review import review
  from backend import storage
  # Disposable audit DB; no user history read or modified.
  with tempfile.TemporaryDirectory() as temp,patch.object(storage,'ROOT',Path(temp)):
   for text in ['对方自称公安要我保密并转账到安全账户，我怎么办？','有人让我开屏幕共享并提供验证码，怎么核实？','这段声音分数很高，能证明是我女儿吗？']:
    report=dict(id='public-agent-test',summary='检测提供线索',modules={'audio':{'status':'completed','score':.82}},transcript={'text':text})
    start=time.monotonic();r=review(report,text,emit=lambda e:print(json.dumps(e,ensure_ascii=False),flush=True))
    out['live'].append(dict(question=text,seconds=time.monotonic()-start,**r))
    (bootstrap.ROOT/'reports/agent-upgrade-check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'question':text,'mode':r['mode'],'seconds':r['duration_seconds'],'trace':r['trace']},ensure_ascii=False),flush=True)
 target=bootstrap.ROOT/'reports/agent-upgrade-check.json';target.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(out['retrieval'],ensure_ascii=False),flush=True)
 if args.live:assert all(r['mode']=='langchain_agent' for r in out['live']),'Actual agent failed; inspect recorded fallback, do not claim success'
if __name__=='__main__':main()
