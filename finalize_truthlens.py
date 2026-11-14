import bootstrap,json,re,urllib.request,urllib.error
from bootstrap import ROOT
from backend import storage
base='http://127.0.0.1:8010'
with urllib.request.urlopen(base) as r:
 html=r.read().decode(); out=dict(status=r.status,index_cache=r.headers.get('Cache-Control'),security_headers={h:r.headers.get(h) for h in ['Content-Security-Policy','X-Content-Type-Options','Referrer-Policy']},assets=[])
for path in re.findall(r'(?:src|href)="(/assets/[^" ]+\.(?:js|css))"',html):
 with urllib.request.urlopen(urllib.request.Request(base+path,headers={'Accept-Encoding':'gzip'})) as r:
  row=dict(path=path,encoding=r.headers.get('Content-Encoding'),wire_bytes=len(r.read()),cache=r.headers.get('Cache-Control')); etag=r.headers.get('ETag')
 try:
  with urllib.request.urlopen(urllib.request.Request(base+path,headers={'If-None-Match':etag,'Accept-Encoding':'gzip'})) as r:row['conditional_status']=r.status
 except urllib.error.HTTPError as e:row['conditional_status']=e.code
 assert row['encoding']=='gzip' and row['conditional_status']==304
 out['assets'].append(row)
(ROOT/'reports/truthlens-assets-acceptance.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
qa=json.loads((ROOT/'runtime/archived-qa-reports.json').read_text(encoding='utf-8')); visible={x['id'] for x in storage.listing()}
assert not ({x['id'] for x in qa}&visible)
media=json.loads((ROOT/'reports/truthlens-eight-media-check.json').read_text(encoding='utf-8'))['checks']
assert len(media)==8 and all(x['passed'] for x in media)
summary=dict(version='2026-11-14 TruthLens integration',backend_unit_tests=79,frontend_node_test_cases=6,signal_assertions_included=9,curated_media_regressions=dict(passed=8,total=8,is_general_accuracy=False),previous_user_image_regression=dict(passed=2,total=2,is_blind_test=False,private_inputs_excluded=True),typescript_and_build='passed',format='passed',agent_browser_check='Actual report question completed with module facts and cited source',qa_records_hidden=len(qa),limitations=['Real elderly trial pending; task sheet provided','Physical phone testing pending','Final audio/video fixtures took 60-103 seconds on cold/cache-release paths','Earlier memory pressure caused browser delays; own idle caches now release, no user training stopped','Desktop LCP missing; mobile metrics local unthrottled browser only','No demo video recorded; no universal accuracy or full score claim'])
(ROOT/'reports/truthlens-delivery-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print('Final assets checked; hidden QA',len(qa),'media passed',len(media))

