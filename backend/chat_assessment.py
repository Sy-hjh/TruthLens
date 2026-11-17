"""Evidence combinations and sourced case analogies, not an authenticity verdict."""
import re
ASSESSMENT_VERSION = 'qinan-chat-evidence-r4'
_IMMEDIATE_TRANSFER = re.compile(
 r'现在(?:就)?(?:请|麻烦|能不能|可以)?你?(?:先)?给我转'
 r'(?:账|款|钱|[0-9０-９一二三四五六七八九十两几]|(?:(?:就(?:可以|行|好)|吧|可以))?[，。！？；]?$)'
)
_BORROWED_CHANNEL = re.compile(
 r'^(?:我)?(?:现在|正在|暂时|刚刚)?(?:是)?(?:拿|用|借(?:用|了|的)?)(?:了|着)?'
 r'(?:别人|朋友|同事|室友|家人|亲戚)(?:的)?(?:手机|电话|账号|微信)'
)
CASE=dict(title='福州：假好友视频借款，10分钟被骗430万元',publisher='汕尾市公安局',date='2023-05-26',url='https://www.shanwei.gov.cn/gdsw110/zwgk/wgk/content/post_924988.html',summary='警方披露，骗子伪装好友视频联系，以保证金和账户过账为由诱导汇款；受害人事后拨打好友电话才发现被骗。',connection='共同点是借熟人身份取得信任，再提出资金要求。相似不代表您这段聊天已被证实是诈骗。')

def enrich(text,signals):
 from .chat_analysis import clauses
 out=list(signals)
 # Recover narrowly defined requests the generative extractor can miss. Each
 # evidence item still copies one exact clause; no synthetic quotes or scores.
 educational=bool(re.search(r'反诈[教育宣传提醒]|防骗提醒|诈骗案例讲解',text))
 borrowed_channel=None
 for quote in (quote for line in text.splitlines() for quote in clauses(line)):
  flat=''.join(quote.split())
  if educational:continue
  if re.search(r'不要|别|切勿|无需|不用',flat[:7]):money=False
  else:money=bool(re.search(r'先借我|借我.{0,8}(?:钱|两千|资金)|给我转(?!发|达|播|交)|转到.{0,12}(?:账户|卡)|打到.{0,12}(?:账户|卡)|汇款|保证金',flat))
  secrecy=bool(re.search(r'(?:别|不要|不能|不许).{0,6}(?:打电话|回拨|联系家人|告诉家人|告诉别人|告诉任何人)|只在这里说',flat))
  pressure=bool(_IMMEDIATE_TRANSFER.search(flat) or re.search(r'十万火急|火烧眉毛|(?:赶紧|马上|立刻|现在就|尽快).{0,12}(?:转账|转.{0,4}钱|打款|汇款|付款|借我|发验证码)',flat))
  if re.search(r'(?:别|不要|切勿|不用|无需)(?:着急|急着|赶紧|马上|立刻|现在|尽快)',flat):pressure=False
  if borrowed_channel is None and _BORROWED_CHANNEL.search(flat):
   borrowed_channel=quote
  for category,matched,title in [('money',money,'请求付款或借款'),('secrecy',secrecy,'阻止独立核实'),('pressure',pressure,'催促立即操作')]:
   if matched and not any(s['category']==category and quote in s['quote'] for s in out):out.append(dict(category=category,title=title,quote=quote,extraction='explicit_request_guard'))
 categories={s['category'] for s in out};money='money' in categories;blocked='secrecy' in categories
 new_account=any(re.search(r'新账户|新卡|另外.{0,3}账户|账户.{0,5}(?:不能用|用不了)',q) and not re.match(r'^(?:请)?(?:不要|别|切勿|无需|不用)',q.strip()) for q in clauses(text))
 kin=bool(re.search(r'妈妈|喂妈|儿子|女儿|孙子|奶奶|爷爷|好友|朋友|领导|老板',text))
 if money and (blocked or (new_account and kin)):
  value=dict(level='alert',title='疑似冒充熟人借款套路' if kin else '借款并阻断核实，存在明显风险组合',summary='对方提出资金要求，还阻止电话核实或更换收款账户。先暂停转账，用原来保存的号码联系本人。',reasons=[s for s in out if s['category'] in {'money','secrecy','identity'}],cases=[CASE] if kin else [])
 elif {'identity','secrecy'}<=categories:
  value=dict(level='alert',title='身份声称加保密要求，疑似冒充机构施压',summary='不要只凭聊天中的身份声称配合操作，请从机构官方渠道核实。',reasons=[s for s in out if s['category'] in {'identity','secrecy','pressure'}],cases=[])
 elif money and 'pressure' in categories and not educational:
  summary='对方称用他人的设备或账号联系，并催你转账。' if borrowed_channel else '对方提出借款并强调紧急。'
  if borrowed_channel and not any(s['category']=='contact_channel' and s['quote']==borrowed_channel for s in out):
   out.append(dict(category='contact_channel',title='声称使用他人的设备或账号',quote=borrowed_channel,extraction='explicit_request_guard'))
  value=dict(level='attention',title='借款并催促，建议先核实',summary=summary+'先暂停付款，用原来保存的号码或其他可信渠道联系本人。',reasons=[s for s in out if s['category'] in {'money','pressure','contact_channel'}],cases=[])
 elif out:
  value=dict(level='attention',title='发现需要核实的要求',summary='请核实下列要求。单独出现借款或身份声称，不能直接认定诈骗。',reasons=out,cases=[])
 else:value=dict(level='uncertain',title='暂未发现明确风险要求',summary='本次未提取到明确风险要求；不代表对方身份已经核实。',reasons=[],cases=[])
 value['basis']='原话要求的组合判断＋公开案例类比，不是70%实验分类器的概率。'
 value['version']=ASSESSMENT_VERSION
 return out,value
