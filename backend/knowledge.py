"""Versioned, human-curated paraphrases of public official guidance; BM25 retrieval."""
import math,re
DOCUMENTS=[
 dict(id='K1',title='亲友借钱：换一个可信渠道核实',url='https://www.zjg.gov.cn/zjgszwz/yjxx/202608/3c16ca084da14d7cbf7661127f97070e.shtml',date='2026-07-18',snippet='遇到视频或语音借钱，应再通过电话或线下见面核实。不要仅因画面和声音熟悉，就跳过确认。',action='callback'),
 dict(id='K2',title='熟人催促汇款：先暂停交易',url='https://legalinfo.moj.gov.cn/zhfxfzzx/fzzxrdtj/202305/t20230525_479513.html',date='2023-05-25',snippet='熟人或领导通过网络诱导汇款时，需要电话、见面等多渠道确认；未经核实不要仓促转账。',action='pause'),
 dict(id='K3',title='保护验证码和个人生物信息',url='https://www.cac.gov.cn/2025-09/22/c_1760258694787465.htm',date='2025-09-22',snippet='谨慎提供人脸等生物信息，不轻易透露身份证、银行卡和验证码。陌生链接、软件和二维码应提高警惕。',action='protect'),
 dict(id='K4',title='账户被冒用也会连累亲友',url='https://www.cac.gov.cn/2025-09/22/c_1760258694787465.htm',date='2025-09-22',snippet='留意账户在陌生设备上的登录，防止社交账号被盗后用于误导亲友。不要把聊天账号本身当作身份凭据。',action='account'),
 dict(id='K5',title='照片与短视频也可能成为伪造素材',url='https://www.zjg.gov.cn/zjgszwz/yjxx/202608/3c16ca084da14d7cbf7661127f97070e.shtml',date='2026-07-18',snippet='不法分子可能收集公开照片、短视频和语音，用于仿冒亲友。不要向不明链接或索要方随意提交这些材料。',action='source')
]
ACTIONS={'pause':'先暂停转账，不根据这份检测报告作出付款决定。','callback':'使用您事先确认并保存的常用号码回拨，或请另一位信任的家人当面核实。','protect':'不要向对方透露短信验证码、密码或银行卡等敏感信息。','account':'请家人通过原先可信的渠道检查账号是否异常，不使用对方临时提供的登录链接。','source':'保留原始聊天与材料出处，谨慎提供个人照片和语音，核对材料的原始来源。'}
SUMMARIES={'verify_identity':'先换一个可信渠道，确认联系您的到底是谁。','inspect_source':'检测只提供线索，还需要核实材料的原始来源。','protect_account':'先保护账户和个人信息，再与家人独立核实。','inconclusive':'现有线索不足以确认真假，请保留人工核实这一步。'}

def tokens(text):
 text=''.join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',text.lower()));return [text[i:i+2] for i in range(max(0,len(text)-1))]

def search(query,limit=3):
 from collections import Counter
 terms=set(tokens(query));docs=[Counter(tokens(d['title']+d['snippet'])) for d in DOCUMENTS];avg=sum(sum(c.values()) for c in docs)/len(docs);scored=[]
 for doc,counts in zip(DOCUMENTS,docs):
  score=0.
  for t in terms:
   tf=counts[t]
   if tf:
    df=sum(c[t]>0 for c in docs);idf=math.log(1+(len(docs)-df+.5)/(df+.5));score+=idf*tf*2.5/(tf+1.5*(.25+.75*sum(counts.values())/avg))
  scored.append(dict(doc,retrieval_score=round(score,5)))
 return sorted(scored,key=lambda x:(-x['retrieval_score'],x['id']))[:limit]
