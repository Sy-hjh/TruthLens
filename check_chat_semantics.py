"""Small transparent semantic regression, not a general accuracy benchmark."""
import bootstrap,json,argparse,time
from backend.chat_analysis import analyze
CASES=[
 ('police_wrapped','16:00\n你好，我是XX市公安局民警，\n你涉嫌一起洗钱案件，现在需要\n配合调查，案情保密，不能告诉\n任何人。\n画江湖 撤回了一条消息\n啊什么案子',{'identity','secrecy'},{'identity','pressure','secrecy'}),
 ('meal','妈今天晚上吃饺子吗？',set(),set()),
 ('privacy','不要给陌生人转账，也别告诉别人验证码。',set(),set()),
 ('colloquial','妈我周转不开，先借我两千，别给我打电话。',{'money','secrecy'},{'money','secrecy'}),
 ('remote','把屏幕共享打开，我来帮你操作手机。',{'remote'},{'remote'}),
 ('six_digits','把刚收到的六位数字念给我。',{'credentials'},{'credentials'}),
 ('ordinary_question','画江湖撤回了一条消息\n啊什么案子',set(),set()),
 ('negative_money','我不需要你转钱，千万别转。',set(),set()),
 ('new_account','老爸，旧卡用不了，你打三千到这张新卡吧。',{'money'},{'money'}),
 ('education','反诈提醒：骗子经常说“案情保密，不能告诉家人”，遇到这种要求要先核实。',set(),set())]
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',default='reports/chat-semantic-review.json');a=p.parse_args();rows=[]
 for label,text,required,allowed in CASES:
  started=time.monotonic()
  try:
   result=analyze(text);actual={s['category'] for s in result['signals']};passed=required<=actual<=allowed
  except Exception as e:result={'error':str(e)};passed=False
  row=dict(case=label,text=text,required=sorted(required),allowed=sorted(allowed),result=result,passed=passed,seconds=round(time.monotonic()-started,2));rows.append(row);print(label,'PASS' if passed else 'FAIL',result,flush=True)
  (bootstrap.ROOT/a.output).write_text(json.dumps(dict(scope='Small observed semantic regression; not general accuracy.',passed=sum(r['passed'] for r in rows),completed=len(rows),planned=len(CASES),checks=rows),ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
