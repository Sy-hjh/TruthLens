"""Offline, self-contained review page; no external scripts or image requests."""
import bootstrap,json,base64,io,html
from pathlib import Path
from PIL import Image
ROOT=bootstrap.ROOT
def main():
    report=ROOT/'reports/domain-evaluation.json'
    scores={r['path']:r for r in json.loads(report.read_text(encoding='utf-8'))['results']} if report.exists() else {}
    localized={r['path']:r for r in json.loads(report.read_text(encoding='utf-8'))['local_edit_results']} if report.exists() else {}
    paths=[ROOT/'data/domain-cases/manifest.json',ROOT/'data/news-cases/manifest.json',ROOT/'data/ps-examples/manifest.json']
    rows=[]
    for path in paths:
        if path.exists():rows.extend(json.loads(path.read_text(encoding='utf-8')))
    cards=[]
    names={'published-real-undamaged':'作者标注：真实正常商品','published-real-damaged':'作者标注：真实破损商品','published-ai-edited':'作者标注：AI改图','traditional-edit-supplement':'传统修改补充（非原图评测）','news':'新闻案例：真假未独立核实'}
    for row in rows:
        kind=row.get('kind','news');score=scores.get(row['path'],{});source=row.get('source_page',row.get('source_url',''))
        with Image.open(ROOT/row['path']) as im:
            im=im.convert('RGB');im.thumbnail((320,260));buffer=io.BytesIO();im.save(buffer,format='JPEG',quality=80)
        uri='data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode()
        details='尚未评测'
        if score:details=f"整图分数 {score['score']:.3f} · 压缩后 {score['jpeg60_score']:.3f}（非诈骗概率）"
        if kind=='news':details='不计准确率，不用于训练'
        local=localized.get(row['path']);map_html=''
        if local:
            details+=f"；局部编辑分数 {local['score']:.3f}"
            if local.get('map'):
                encoded=base64.b64encode((ROOT/local['map']).read_bytes()).decode()
                map_html=f'<details><summary>模型异常分布图</summary><img src="data:image/png;base64,{encoded}" alt="模型预测异常图"><p>亮处是预测异常，不是已证实的修改范围。</p></details>'
        cards.append(f'''<article data-kind="{html.escape(kind)}"><img loading="lazy" src="{uri}" alt="商品案例缩略图"><h3>{html.escape(names.get(kind,kind))}</h3><p>{html.escape(row.get('category',row.get('title','')))}</p><p>{html.escape(row.get('generator',''))}</p><p>{html.escape(details)}</p>{map_html}<small>{html.escape(row.get('group',''))}</small><p><a href="{html.escape(source,quote=True)}" target="_blank" rel="noopener noreferrer">公开来源</a></p></article>''')
    document='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>亲安 · 商品域案例检查</title><style>body{font:18px/1.6 system-ui;background:#f3f6f4;color:#173e35;margin:24px}header{max-width:1000px}select{font:inherit;padding:10px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:18px;margin-top:24px}article{background:white;padding:16px;border:1px solid #d5dfda;border-radius:12px;overflow-wrap:anywhere}img{width:100%;height:240px;object-fit:contain}h3{font-size:19px}small{color:#52655c}[hidden]{display:none!important}</style><header><h1>商品域案例检查</h1><p>这是本机离线检查册，图片与来源已整理。240张商品案例使用作者标签；新闻图片没有独立真假标签，不参与训练和准确率。AI改图不同于整张生成；整图低分不证明局部没有修改。</p><p>当前全部案例留作外部排查，尚未加入训练。缩略图仅用于查看，模型检测使用下载的原始文件。</p><label>筛选 <select id="filter"><option value="all">全部</option>OPTIONS</select></label><p id="count"></p></header><main>CARDS</main><script>const select=document.querySelector('select');select.onchange=()=>{let count=0;document.querySelectorAll('article').forEach(a=>{a.hidden=select.value!=='all'&&a.dataset.kind!==select.value;if(!a.hidden)count++});document.querySelector('#count').textContent='当前显示 '+count+' 张'};select.onchange();</script></html>'''
    present={r.get('kind','news') for r in rows}
    options=''.join(f'<option value="{k}">{v}</option>' for k,v in names.items() if k in present)
    (ROOT/'商品案例检查.html').write_text(document.replace('OPTIONS',options).replace('CARDS',''.join(cards)),encoding='utf-8')
    print('Offline gallery rows',len(rows))
if __name__=='__main__':main()
