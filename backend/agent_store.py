"""Local operational evidence. No questions, transcripts, contacts or raw media in audits."""
import json,sqlite3
from contextlib import contextmanager
from datetime import datetime,timezone
from . import storage

@contextmanager
def connect():
 db=sqlite3.connect(storage.ROOT/'agent.sqlite3',timeout=10)
 db.execute('CREATE TABLE IF NOT EXISTS audits (id TEXT PRIMARY KEY, case_id TEXT, created TEXT, body TEXT)')
 db.execute('CREATE TABLE IF NOT EXISTS feedback (case_id TEXT PRIMARY KEY, verdict TEXT, created TEXT)')
 try:
  with db:yield db
 finally:db.close()

def save_audit(case_id,result):
 body={k:result[k] for k in ('mode','duration_seconds','trace','agent_error')}
 with connect() as db:db.execute('INSERT INTO audits VALUES (?,?,?,?)',(result['run_id'],case_id,datetime.now(timezone.utc).isoformat(),json.dumps(body,ensure_ascii=False)))

def feedback(case_id,verdict):
 if verdict not in {'useful','not_useful','false_alarm','missed_risk'}:raise ValueError('Unknown feedback')
 with connect() as db:db.execute('INSERT OR REPLACE INTO feedback VALUES (?,?,?)',(case_id,verdict,datetime.now(timezone.utc).isoformat()))
 return {'saved':True,'used_for_training':False,'note':'仅用于人工复核统计，不会直接改变检测模型。'}

def delete(case_id):
 with connect() as db:
  db.execute('DELETE FROM audits WHERE case_id=?',(case_id,));db.execute('DELETE FROM feedback WHERE case_id=?',(case_id,))

def stats():
 with connect() as db:
  rows=[json.loads(r[0]) for r in db.execute('SELECT body FROM audits ORDER BY rowid DESC LIMIT 1000')]
  counts=dict(db.execute('SELECT verdict,COUNT(*) FROM feedback GROUP BY verdict'))
 return dict(runs=len(rows),agent_completed=sum(r['mode']=='langchain_agent' for r in rows),fallback_runs=sum(r['mode']!='langchain_agent' for r in rows),feedback=counts,note='运行和自报反馈统计，不是模型准确率或真实防骗效果。')
