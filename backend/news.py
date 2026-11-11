"""Public anti-fraud alerts, fixed source allowlist, cache and honest timestamps."""
import json,re,html,threading,logging
from datetime import datetime,timezone
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import requests
from bootstrap import ROOT
_lock=threading.Lock();CACHE=ROOT/'runtime/news-cache.json'
SEED=[dict(id='seed-recall',title='警惕“车辆召回”短信诈骗陷阱',url='https://12321.cn/arc?aid=12158.html',published_at='2026-11-09',source='12321举报中心',topic='车辆召回',tip='自行打开车企官方渠道核对召回信息，不通过短信链接填写银行卡或验证码。'),dict(id='seed-pension',title='防范非法养老APP诈骗的提示',url='https://www.xinhuanet.com/politics/20260922/9c34577e51c14008ba12127d9dc950f4/c.html',published_at='2026-09-22',source='民政部（新华网转载）',topic='养老补贴',tip='补贴项目先向官方核实。要求先交激活费、保证金或充值返利时，不要付款。'),dict(id='seed-face',title='骗取人脸信息的诈骗套路要认清',url='https://www.cac.gov.cn/2026-09/20/c_1791660743251428.htm',published_at='2026-09-20',source='中央网信办',topic='人脸信息',tip='陌生人要求做动作、念数字或提交身份证时，先核实用途，不下载来路不明的软件。')]
def _tip(title):
 for words,topic,tip in [(['召回','车辆'],'车辆召回','自行通过车企官方渠道查证，不从短信链接填写银行卡和验证码。'),(['地震','泥石流','捐赠'],'捐赠骗局','捐助前核对正规机构的官方渠道，不扫描陌生群消息中的付款码。'),(['养老','老年','补贴'],'养老补贴','向民政等官方渠道核实项目，不先交激活费、保证金。'),(['抢票','票务','观赛'],'票务骗局','在官方平台核对订单，不为所谓优先出票支付额外保证金。'),(['贷款','催收'],'贷款骗局','核实机构及合同，不因陌生催收来电提供验证码或仓促转账。'),(['APP','仿冒'],'仿冒应用','从正规渠道核对应用及开发者，不安装陌生客服发来的软件。')]:
  if any(w in title for w in words):return topic,tip
 return '新型骗局','换一个可信的官方渠道核实，别按陌生消息提供的新号码或链接付款。'
def _read():
 try:return json.loads(CACHE.read_text(encoding='utf-8'))
 except (OSError,ValueError):return dict(items=SEED,checked_at=None,last_error=None)
def refresh():
 if not _lock.acquire(blocking=False):return
 try:
  r=requests.get('https://12321.cn/warn',timeout=(5,12));r.raise_for_status();r.encoding='utf-8';links=[]
  for match in re.finditer(r'<a\b[^>]*href=[\"\']([^\"\']+)[\"\'][^>]*>(.*?)</a>',r.text,re.S|re.I):
   title=html.unescape(re.sub('<[^>]+>','',match.group(2))).strip();url=urljoin('https://12321.cn',match.group(1))
   if re.fullmatch(r'https://12321\.cn/arc\?aid=\d+\.html',url) and '提醒' in title and any(w in title for w in ['诈骗','骗局','陷阱','风险']):links.append((url,title[:160]))
  if not links:raise ValueError('来源页面没有可验证的预警链接')
  def fetch(item):
   url,title=item;p=requests.get(url,timeout=(5,10));p.raise_for_status();p.encoding='utf-8';plain=html.unescape(re.sub('<[^>]+>',' ',p.text));dates=re.findall(r'20\d{2}[-/]\d{2}[-/]\d{2}',plain)
   if not dates:return None
   date=dates[0].replace('/','-')
   if date>datetime.now(timezone.utc).date().isoformat():return None
   topic,tip=_tip(title);return dict(id='12321-'+re.search(r'aid=(\d+)',url)[1],title=title,url=url,published_at=date,source='12321举报中心',topic=topic,tip=tip)
  items=[]
  with ThreadPoolExecutor(max_workers=3) as pool:
   futures=[pool.submit(fetch,item) for item in links[:8]]
   for f in futures:
    try:
     row=f.result()
     if row:items.append(row)
    except requests.RequestException:pass
  if not items:raise ValueError('未取得带发布日期的预警')
  unique={x['url']:x for x in SEED+items};data=dict(items=sorted(unique.values(),key=lambda x:x['published_at'],reverse=True)[:12],checked_at=datetime.now(timezone.utc).isoformat(),last_error=None)
  temp=CACHE.with_suffix('.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(CACHE)
 except Exception:
  logging.exception('News update failed; retaining known sources');data=_read();data['last_error']='暂未连上新闻来源，显示已保存的预警。';CACHE.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 finally:_lock.release()
def get_news(update=False):
 data=_read();stale=True
 if data.get('checked_at'):
  try:stale=(datetime.now(timezone.utc)-datetime.fromisoformat(data['checked_at'])).total_seconds()>21600
  except ValueError:pass
 if (update or stale) and not _lock.locked():threading.Thread(target=refresh,daemon=True).start()
 return dict(data,updating=_lock.locked(),update_interval_hours=6)
def start_updates(stop):
 def loop():
  while not stop.is_set():
   refresh()
   if stop.wait(21600):break
 threading.Thread(target=loop,daemon=True,name='qinan-public-news').start()
if __name__=='__main__':refresh();print(json.dumps(get_news(),ensure_ascii=False,indent=2))
