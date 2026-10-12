"""Readable research deliverables. Standard-library only, no network. No score implies authenticity."""
import argparse,base64,csv,hashlib,html,json,re,textwrap
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

STATUS={'image_verified':'原件影像已核对','fulltext_verified':'正式全文已核对','metadata_only':'仅元数据已核对','search_lead':'搜索线索','unverified':'未核验','abstract_checked':'摘要与元数据已读'}
CATEGORY={'original':'原件／影像','edited_primary':'编辑史料','contemporary_public':'同时代公开资料','finding_aid':'目录／检索工具','secondary':'二手研究','memoir':'回忆资料','unverified':'性质待核'}
STANCE={'support':'支持','partial':'部分支持','contradict':'反证','undetermined':'无法判断','expected_missing':'预期材料缺失'}
COLOR={'support':'#788C5D','partial':'#C78E3F','contradict':'#B04A4A','undetermined':'#5C7CA3','expected_missing':'#87867F'}
LITERATURE_FIELDS=['literature_id','title','author','year','publication','research_question','method','findings','primary_source_leads','verification_status','url','claim_ids','notes']
def esc(x):return html.escape(str(x if x is not None else '待核'),quote=True)
def display(x):return '；'.join(str(i) for i in x) if isinstance(x,list) else str(x) if x is not None else '待核'
def safe_url(u):
 if not u:return False
 try:return urlparse(u).scheme in ('http','https') and bool(urlparse(u).hostname) and not any(c.isspace() for c in u)
 except ValueError:return False

def validate_literature(bundle):
 from source_tools import schema_check,read_json,valid_date
 rows=bundle.get('literature',[])
 if not isinstance(rows,list):raise ValueError('literature must be array')
 schema=read_json(Path(__file__).resolve().parents[1]/'assets/literature-record.schema.json');seen=set();errors=[];claims={c['claim_id'] for c in bundle.get('claims',[])}
 for i,r in enumerate(rows):
  schema_check(r,schema,f'literature[{i}]',errors)
  if not isinstance(r,dict):continue
  if r.get('literature_id') in seen:errors.append('duplicate literature_id')
  seen.add(r.get('literature_id'))
  if r.get('url') and not safe_url(r['url']):errors.append('unsafe literature URL')
  if r.get('year') and not valid_date(r['year']):errors.append('invalid literature year')
  if any(cid not in claims for cid in r.get('claim_ids',[])):errors.append('unknown literature claim_id')
  if r.get('verification_status') in ('metadata_only','search_lead','unverified') and any(r.get(k) for k in ('method','findings')):errors.append('unread literature cannot contain method/findings; read abstract or fulltext first')
  if r.get('verification_status') in ('fulltext_verified','abstract_checked') and not r.get('notes'):errors.append('read literature requires scope/locator in notes')
 if errors:raise ValueError('\n'.join(errors))
 return rows

def chart_data(bundle):
 rows=bundle['sources'];claims=[]
 for c in bundle.get('claims',[]):
  evidence=[dict(e,record_id=r['record_id'],verification=r['content_verification_status']) for r in rows for e in r['claim_evidence'] if e['claim_id']==c['claim_id']]
  claims.append(dict(c,evidence=evidence))
 timeline=[{'record_id':r['record_id'],'title':r['document_title_original'] or '题名待核','date':r['document_date'],'precision':r['document_date_precision'],'status':r['content_verification_status']} for r in rows if r.get('document_date')]
 timeline.sort(key=lambda r:(r['date'],r['record_id']))
 return {'source_count':len(rows),'literature_count':len(bundle.get('literature',[])),'verification_counts':dict(Counter(r['content_verification_status'] or 'unverified' for r in rows)),'claims':claims,'timeline':timeline,'undated':[r['record_id'] for r in rows if not r.get('document_date')],'note':'记录数不是独立史料数；连线/单元格表示命题对应，不是因果效应。'}

def svg_start(width,height,title):
 return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}"><title>{esc(title)}</title><rect width="100%" height="100%" fill="#FAF9F5"/><style>text{{font-family:system-ui,-apple-system,sans-serif;fill:#141413}} .muted{{fill:#87867F}} .small{{font-size:12px}}</style>'
def svg_text(x,y,text,size=14,extra=''):
 return f'<text x="{x}" y="{y}" font-size="{size}" {extra}>{esc(text)}</text>'
def timeline_svg(data):
 rows=data['timeline'];height=max(230,100+len(rows)*78);s=svg_start(1100,height,'史料形成时间线')+svg_text(30,35,'史料形成时间线 · 非因果链',22)
 s+=svg_text(30,60,'只使用文书形成日期；约年/月精度保留，未归一化日期另列。',12,'class="muted"')
 if rows:s+=f'<line x1="196" y1="93" x2="196" y2="{93+max(0,len(rows)-1)*78}" stroke="#D1CFC5" stroke-width="2"/>'
 for i,r in enumerate(rows):
  y=100+i*78;s+=f'<circle cx="196" cy="{y}" r="6" fill="#D97757"/>'+svg_text(32,y+5,r['date'])+svg_text(32,y+24,'精度：'+str(r['precision']),11,'class="muted"')
  s+=svg_text(218,y+4,r['record_id'],13)+svg_text(218,y+26,textwrap.shorten(r['title'],width=103,placeholder='…'),13)+svg_text(218,y+47,STATUS.get(r['status'],r['status']),11,'class="muted"')
 if not rows:s+=svg_text(30,115,'暂无可归一化形成日期，不补造时间点。')
 if data['undated']:s+=svg_text(30,height-18,'未入时间线：'+', '.join(data['undated']),11,'class="muted"')
 return s+'</svg>'
def verification_svg(data):
 counts=data['verification_counts'];order=[k for k in STATUS if k in counts];height=max(220,100+len(order)*48);s=svg_start(900,height,'核验层级分布')+svg_text(30,35,'核验层级 · 记录计数',22)+svg_text(30,60,'反映本次读取层级，不是可信度评分，也不是独立来源数量。',12,'class="muted"');max_count=max(counts.values(),default=1)
 for i,k in enumerate(order):
  y=90+i*48;n=counts[k];w=480*n/max_count
  s+=svg_text(30,y+20,STATUS.get(k,k),13)+f'<rect x="240" y="{y}" width="{w}" height="26" rx="5" fill="'+('#788C5D' if k in ('image_verified','fulltext_verified') else '#5C7CA3')+'"/>'+svg_text(740,y+20,str(n),15)
 if not order:s+=svg_text(30,115,'本次没有史料记录。')
 return s+'</svg>'
def claim_svg(data,rows):
 cs=data['claims'];cw=165;left=255;width=max(1000,left+len(cs)*cw+35);height=max(250,175+len(rows)*52);s=svg_start(width,height,'命题—史料对应图')+svg_text(30,35,'命题—史料对应图',22)
 s+=svg_text(30,60,'颜色表示支持方向；空白表示未建立对应。目录材料的正文命题保持无法判断。',12,'class="muted"')
 for j,c in enumerate(cs):
  x=left+j*cw;s+=svg_text(x+8,92,c['claim_id'],13)
  for k,line in enumerate(textwrap.wrap(c['text'],width=12)[:3]):s+=svg_text(x+8,111+k*15,line,11)
 for i,r in enumerate(rows):
  y=160+i*52;s+=f'<a href="#source-{esc(r["record_id"])}">'+svg_text(30,y+24,r['record_id'],12)+'</a>'
  for j,c in enumerate(cs):
   e=[x for x in c['evidence'] if x['record_id']==r['record_id']];x=left+j*cw
   if e:
    st=e[0]['stance'];color=COLOR[st];label=STANCE[st]+({'direct':' · 直接','indirect':' · 间接'}.get(e[0]['proof_value'],''));tip='；'.join(z['basis']+' / '+str(z.get('limitations') or '')+' / '+STATUS.get(z['verification'],z['verification']) for z in e)
    s+=f'<g><title>{esc(tip)}</title><rect x="{x}" y="{y}" width="{cw-10}" height="36" rx="6" fill="{color}" fill-opacity="0.15" stroke="{color}" stroke-width="1.5"/>'+svg_text(x+10,y+24,label,12)+'</g>'
   else:s+=f'<rect x="{x}" y="{y}" width="{cw-10}" height="36" rx="6" fill="#F0EEE6"/>'+svg_text(x+10,y+24,'—',12)
 if not cs:s+=svg_text(30,115,'未提供研究命题，不自动推演命题。')
 elif not rows:s+=svg_text(30,175,'没有史料记录；命题保留为检索缺口。')
 return s+'</svg>'

SOURCE_COLUMNS=['编号','史料名称','形成日期','作者／机构','性质','原收藏机构','馆藏号','内容核验','对应命题','研究用途','局限','原始链接']
LIT_COLUMNS=['编号','文献题名','作者','年份','出版物','研究问题','方法／材料','主要观点','史料线索','对应命题','阅读状态','核验范围／缺口','链接']
CLAIM_COLUMNS=['命题编号','研究命题','支持史料','部分支持','反证史料','无法判断','材料缺口']
def matrices(bundle):
 sources=[]
 for r in bundle['sources']:
  sources.append(dict(zip(SOURCE_COLUMNS,[r['record_id'],r['document_title_original'],r['document_date'] or r['document_date_raw'],r['creator'],CATEGORY.get(r['source_category'],r['source_category']),r['original_repository'],r['archive_reference'] or r['item_identifier'],STATUS.get(r['content_verification_status'],r['content_verification_status']),'; '.join(e['claim_id']+':'+STANCE[e['stance']] for e in r['claim_evidence']),r['research_relevance'],r['source_criticism'] or '; '.join(r['remaining_uncertainties']),r['fulltext_url'] or r['catalogue_url'] or r['digital_image_url']])))
 literature=[dict(zip(LIT_COLUMNS,[r['literature_id'],r['title'],r['author'],r['year'],r['publication'],r['research_question'],r['method'],r['findings'],r['primary_source_leads'],r['claim_ids'],STATUS.get(r['verification_status'],r['verification_status']),r['notes'],r['url']])) for r in bundle.get('literature',[])]
 claims=[]
 for c in chart_data(bundle)['claims']:
  def ids(stance):return '; '.join(e['record_id'] for e in c['evidence'] if e['stance']==stance)
  gaps=ids('expected_missing') or ('尚无对应史料' if not c['evidence'] else '仍需结合各条材料的局限核查')
  claims.append(dict(zip(CLAIM_COLUMNS,[c['claim_id'],c['text'],ids('support'),ids('partial'),ids('contradict'),ids('undetermined'),gaps])))
 return sources,literature,claims

def table_html(rows,columns,kind,statuses=None):
 head='<thead><tr>'+''.join('<th scope="col">'+esc(c)+'</th>' for c in columns)+'</tr></thead>';body=''
 for i,r in enumerate(rows):
  body+=f'<tr data-kind="{kind}" data-status="{esc((statuses or [None]*len(rows))[i])}" data-search="{esc(" ".join(display(v) for v in r.values()).lower())}">'
  for c in columns:
   val=r[c]
   if c in ('链接','原始链接') and safe_url(val):cell=f'<a href="{esc(val)}" target="_blank" rel="noopener noreferrer">来源页面 ↗</a>'
   elif c=='编号' and kind=='sources':cell=f'<a href="#source-{esc(val)}">{esc(val)}</a>'
   else:cell=esc(display(val))
   body+='<td>'+cell+'</td>'
  body+='</tr>'
 return '<div class="table-wrap"><table class="panel-table" id="'+kind+'-table">'+head+'<tbody>'+body+'</tbody></table></div>'

def source_cards(rows,style,custom=None):
 from source_tools import citation
 cards=''
 for r in rows:
  c=citation(r,style,custom);foot=c.get('first_note') or c.get('reason') or '引注待核';url=r['fulltext_url'] or r['catalogue_url'] or r['digital_image_url']
  cards+=f'<details id="source-{esc(r["record_id"])}" class="source-card"><summary><span class="mono">{esc(r["record_id"])}</span> {esc(r["document_title_original"])} <span class="badge">{esc(STATUS.get(r["content_verification_status"],r["content_verification_status"]))}</span></summary><div class="card-content">'
  chain=' → '.join(str(r[k]) for k in ('original_repository','fonds_or_collection','series','file_unit','item_identifier','original_page_or_folio') if r.get(k)) or '原档收藏链待核'
  for label,value in [('形成时间',r['document_date'] or r['document_date_raw']),('作者／收件人',display(r['creator'])+' / '+display(r['recipient'])),('馆藏路径',chain),('原档号',r['archive_reference']),('在线提供者',r['online_host']),('数字制作／编辑者',r['digital_producer']),('研究用途',r['research_relevance']),('史料批判',r['source_criticism']),('追溯说明',r['provenance_notes']),('引注草稿',foot),('待解决问题',r['remaining_uncertainties'])]:
   cards+=f'<div class="field"><b>{esc(label)}</b><span>{esc(display(value))}</span></div>'
  if r['original_text_excerpt']:cards+=f'<div class="excerpt"><b>已读取短原文</b><blockquote>{esc(r["original_text_excerpt"])}</blockquote><p>{esc(r["excerpt_translation"])}</p><p class="mono">{esc(r["excerpt_location"])}</p></div>'
  if safe_url(url):cards+=f'<p><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">打开所用来源页面 ↗</a></p>'
  cards+='</div></details>'
 return cards or '<p>本次没有史料卡片。</p>'

CSS='''
:root {--ivory:#FAF9F5;--slate:#141413;--clay:#D97757;--clay-d:#B85C3E;--oat:#E3DACC;--olive:#788C5D;--rust:#B04A3F;--white:#FFFFFF;--gray-100:#F0EEE6;--gray-300:#D1CFC5;--gray-500:#87867F;--gray-700:#3D3D3A;--success:#788C5D;--warning:#C78E3F;--danger:#B04A4A;--info:#5C7CA3;--serif:ui-serif,Georgia,"Times New Roman",Times,serif;--sans:system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;--mono:ui-monospace,"SF Mono",Menlo,Monaco,Consolas,monospace;--radius-panel:12px;--radius-row:8px;--radius-pill:999px;--border:1.5px solid var(--gray-300);--shadow-sm:0 1px 2px rgba(20,20,19,.06);--shadow-md:0 4px 10px rgba(20,20,19,.08);--shadow-lg:0 12px 28px rgba(20,20,19,.12)}
*{box-sizing:border-box}body{margin:0;padding:56px 24px 96px;background:var(--ivory);color:var(--slate);font:430 14px/1.6 var(--sans);-webkit-font-smoothing:antialiased}.page{max-width:1450px;margin:auto}header{max-width:960px}h1,h2,h3{font-family:var(--serif);font-weight:500;letter-spacing:-.02em}h1{font-size:44px;line-height:1.2;margin:14px 0}h2{font-size:26px;margin-top:0}.sub{font-size:16px;color:var(--gray-700);max-width:850px}.eyebrow,.mono,footer,label,.stat-label{font-family:var(--mono);font-size:12px}.eyebrow{color:var(--clay);letter-spacing:.12em}.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:32px 0}.stat-card,.panel{background:var(--white);border:var(--border);border-radius:12px;padding:22px}.stat-card{transition:transform 150ms ease,box-shadow 150ms ease}.stat-card:hover{transform:translateY(-3px);box-shadow:var(--shadow-md)}.stat-num{font:500 34px var(--serif)}.stat-label{color:var(--gray-500)}.toolbar{display:flex;gap:12px;flex-wrap:wrap;align-items:end;margin:18px 0}.toolbar label{display:block;color:var(--gray-700)}input,select,button{font:500 14px var(--sans);border:var(--border);border-radius:8px;background:var(--white);color:var(--slate)}input,select{height:38px;padding:0 12px}input{width:320px;max-width:90vw}button{height:36px;padding:0 14px;cursor:pointer;transition:background 150ms ease}button:hover{background:var(--oat)}button.primary{background:var(--clay);border-color:var(--clay);color:var(--white)}button.primary:hover{background:var(--clay-d)}button[aria-pressed=true]{border-color:var(--clay);color:var(--clay-d)}a{color:var(--clay-d);text-underline-offset:3px}.rule{border:0;border-top:var(--border);margin:16px 0 20px}section{margin-top:36px}.table-wrap{overflow:auto;border:var(--border);border-radius:12px;background:var(--white)}table.panel-table{width:100%;min-width:2600px;border-collapse:collapse;font-size:13px}th{background:var(--gray-100);color:var(--gray-700);text-align:left;font-size:12px;position:sticky;top:0}td,th{padding:13px 16px;border-bottom:var(--border);vertical-align:top}td:nth-child(1){min-width:150px}td:nth-child(2){min-width:320px;max-width:380px}td:nth-child(7){min-width:330px}td{min-width:95px;max-width:280px;overflow-wrap:anywhere}tbody tr:hover{background:var(--ivory)}.muted{color:var(--gray-500)}.notice{border-left:4px solid var(--clay);padding:12px 18px;background:var(--oat);border-radius:8px}.charts{display:grid;grid-template-columns:1.2fr 1fr;gap:20px}.chart{overflow:auto}.chart svg{width:100%;height:auto;min-width:550px;display:block}.diagram svg{min-width:900px}.chart-head{display:flex;justify-content:space-between;align-items:center}.badge{display:inline-block;font-size:11px;border-radius:999px;padding:2px 9px;background:var(--gray-100);color:var(--gray-700)}details{margin-top:12px;background:var(--white);border:var(--border);border-radius:12px;scroll-margin-top:16px}summary{padding:17px;cursor:pointer;overflow-wrap:anywhere}summary .mono{color:var(--clay-d)}.card-content{padding:0 22px 22px}.field{display:grid;grid-template-columns:130px 1fr;gap:12px;padding:9px 0;border-bottom:var(--border)}.field b{font-size:12px;color:var(--gray-500);font-weight:500}.field span{overflow-wrap:anywhere}.excerpt{margin:18px 0;background:var(--gray-100);padding:16px;border-radius:8px}blockquote{margin:12px 0;font-family:var(--serif)}.tabs{display:flex;gap:8px}.tabs button{min-width:100px}[hidden]{display:none!important}footer{margin-top:50px;padding-top:18px;border-top:var(--border);color:var(--gray-500)}.copy-box{width:100%;min-height:140px;padding:12px;display:none}noscript{display:block}.nowrap{white-space:nowrap}@media(max-width:880px){.charts{grid-template-columns:1fr}h1{font-size:36px}}@media(max-width:720px){.stat-grid{grid-template-columns:repeat(2,1fr)}body{padding:32px 16px 60px}}@media(max-width:640px){.field{grid-template-columns:1fr}.toolbar{align-items:stretch}.toolbar input{width:100%}h1{font-size:30px}}@media print{body{padding:0}.toolbar,.tabs,.download{display:none}.panel{break-inside:avoid}.table-wrap{overflow:visible}table.panel-table{min-width:0;font-size:9px}td,th{min-width:0;padding:5px}details{break-inside:avoid}details .card-content{display:block!important}.chart svg{min-width:0}.charts{display:block}}
'''
JS='''
const DATA=__DATA__;let active='sources';const $=id=>document.getElementById(id);
function filter(){const q=$('query').value.toLowerCase().trim(),status=$('status').value;let n=0;document.querySelectorAll('#'+active+'-table tbody tr').forEach(row=>{row.hidden=!(row.dataset.search.includes(q)&&(!status||row.dataset.status===status));if(!row.hidden)n++;});$('count').textContent='当前显示 '+n+' 条';}
function activate(kind){active=kind;document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.tab===kind)));$('sources-panel').hidden=kind!=='sources';$('literature-panel').hidden=kind!=='literature';$('status').value='';filter();}
document.querySelectorAll('[data-tab]').forEach(b=>b.addEventListener('click',()=>activate(b.dataset.tab)));
$('query').addEventListener('input',filter);$('status').addEventListener('change',filter);$('reset').addEventListener('click',()=>{$('query').value='';$('status').value='';filter();});
$('sort').addEventListener('click',()=>{const body=$ (active+'-table').tBodies[0];[...body.rows].sort((a,b)=>a.cells[active==='sources'?2:3].textContent.localeCompare(b.cells[active==='sources'?2:3].textContent)).forEach(r=>body.appendChild(r));});
function download(name,text,type){const blob=new Blob([text],{type});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
$('csv').addEventListener('click',()=>{const rows=[...$(active+'-table').rows].filter(r=>!r.hidden);const cell=s=>{if(/^[\\s]*[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};download(active+'-filtered.csv','\\ufeff'+rows.map(r=>[...r.cells].map(c=>cell(c.querySelector('a[href^="http"]')?.href || c.textContent)).join(',')).join('\\r\\n'),'text/csv;charset=utf-8');});
$('copy').addEventListener('click',async()=>{const ids=[...$('sources-table').tBodies[0].rows].filter(r=>!r.hidden).map(r=>r.cells[0].textContent);const text=DATA.citations.filter(c=>ids.includes(c.record_id)&&c.status==='complete').map(c=>c.first_note).join('\\n\\n');$('copy-result').textContent=text?'下方显示当前史料的已核正文引注草稿，可直接选中复制。':'当前筛选没有可用的正文引注。';$('copy-box').style.display='block';$('copy-box').value=text;try{await navigator.clipboard.writeText(text);$('copy-result').textContent='已复制 '+DATA.citations.filter(c=>ids.includes(c.record_id)&&c.status==='complete').length+' 条正文引注。';}catch(e){$('copy-box').focus();$('copy-box').select();}});
$('print').addEventListener('click',()=>window.print());document.querySelectorAll('a[href^="#source-"]').forEach(a=>a.addEventListener('click',event=>{event.preventDefault();const d=document.getElementById(a.getAttribute('href').slice(1));if(d){d.open=true;d.scrollIntoView({block:'start'});}}));filter();
'''

def markdown_table(rows,columns):
 def m(x):return display(x).replace('|','\\|').replace('\n','<br>')
 return '| '+' | '.join(columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+''.join('| '+' | '.join(m(r[c]) for c in columns)+' |\n' for r in rows)

def build_report(bundle,out,title='历史史料研究矩阵',style='zh',custom=None,validated=False):
 from source_tools import export_bundle,citation,cell
 if not validated:
  export_bundle(bundle,out,style,custom,include_report=False)
 validate_literature(bundle);out.mkdir(parents=True,exist_ok=True);d=chart_data(bundle);sources,lit,claims=matrices(bundle)
 for name,rows,columns in [('source-matrix',sources,SOURCE_COLUMNS),('literature-matrix',lit,LIT_COLUMNS),('claim-matrix',claims,CLAIM_COLUMNS)]:
  with (out/(name+'.csv')).open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows({k:cell(v) for k,v in r.items()} for r in rows)
  (out/(name+'.md')).write_text(markdown_table(rows,columns),encoding='utf-8')
 charts={'timeline.svg':timeline_svg(d),'verification.svg':verification_svg(d),'claim-evidence.svg':claim_svg(d,bundle['sources'])}
 for name,svg in charts.items():(out/name).write_text(svg,encoding='utf-8')
 (out/'chart-data.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'literature.json').write_text(json.dumps(bundle.get('literature',[]),ensure_ascii=False,indent=2),encoding='utf-8')
 citations=[dict(record_id=r['record_id'],**citation(r,style,custom)) for r in bundle['sources']]
 body_read=sum(n for k,n in d['verification_counts'].items() if k in ('image_verified','fulltext_verified'))
 stats=[(d['source_count'],'史料记录'),(d['literature_count'],'研究文献'),(len(d['claims']),'待考证命题'),(body_read,'已读取史料正文')]
 data={'citations':citations};payload=json.dumps(data,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026').replace('\u2028','\\u2028').replace('\u2029','\\u2029');script=JS.replace('__DATA__',payload);digest=base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
 page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'+f'<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'sha256-{digest}\'; img-src data:; connect-src \'none\'; base-uri \'none\'; form-action \'none\'">'+f'<title>{esc(title)}</title><style>{CSS}</style></head><body><div class="page"><header><div class="eyebrow">HISTORICAL SOURCE RESEARCH / 研究矩阵</div><h1>{esc(title)}</h1><p class="sub">从研究问题查到材料，从材料追到具体命题。阅读矩阵、对照图表，并打开每条史料卡片检查出处、核验范围与脚注。</p></header>'
 page+='<div class="stat-grid">'+''.join(f'<div class="stat-card"><div class="stat-num">{n}</div><div class="stat-label">{label}</div></div>' for n,label in stats)+'</div><p class="notice">'+esc(bundle.get('research_summary') or '这是本次资料集合的研究视图。记录数不是独立来源数；目录与摘要不等于全文。图表呈现时间与证据对应，不自动证明因果。')+'</p>'
 page+='<section id="matrix"><h2>史料与文献矩阵</h2><hr class="rule"><div class="tabs"><button data-tab="sources" aria-pressed="true">史料矩阵</button><button data-tab="literature" aria-pressed="false">文献矩阵</button></div><div class="toolbar"><div><label for="query">题名、作者、馆藏号或命题</label><input id="query" type="search" placeholder="输入关键词筛选"></div><div><label for="status">核验／阅读状态</label><select id="status"><option value="">全部状态</option>'+''.join(f'<option value="{k}">{v}</option>' for k,v in STATUS.items())+'</select></div><button id="reset">清除筛选</button><button id="sort">按日期／年份排序</button><button id="csv">下载当前矩阵 CSV</button><button id="copy" class="primary">复制史料脚注</button><button id="print">打印／保存 PDF</button></div><p id="count" class="mono" aria-live="polite"></p><noscript>JavaScript未启用：史料矩阵、图表和史料卡片仍可阅读；文献矩阵请打开同目录 literature-matrix.csv。</noscript>'
 page+='<div id="sources-panel">'+table_html(sources,SOURCE_COLUMNS,'sources',[r['content_verification_status'] for r in bundle['sources']])+'</div><div id="literature-panel" hidden>'+table_html(lit,LIT_COLUMNS,'literature',[r['verification_status'] for r in bundle.get('literature',[])])+'</div><p id="copy-result" aria-live="polite" class="muted"></p><textarea id="copy-box" class="copy-box" aria-label="可复制引注"></textarea></section>'
 page+='<section><h2>历史时间与核验层级</h2><hr class="rule"><div class="charts">'+''.join(f'<div class="panel chart"><div class="chart-head"><span class="mono">{label}</span><a class="download" href="{name}" download>下载 SVG</a></div>{charts[name]}</div>' for name,label in [('timeline.svg','形成日期'),('verification.svg','本次核验范围')])+'</div></section>'
 page+='<section><h2>命题与证据对应</h2><hr class="rule"><div class="panel chart diagram"><p><a class="download" href="claim-evidence.svg" download>下载 SVG</a> · 点击史料编号打开卡片，悬停色块查看对应理由。</p>'+charts['claim-evidence.svg']+'</div>'+table_html(claims,CLAIM_COLUMNS,'claims')+'</section><section><h2>可查读的史料卡片</h2><hr class="rule">'+source_cards(bundle['sources'],style,custom)+'</section>'
 page+='<footer>依据本次sources / literature / claims / search_log记录生成 · 日期精度与版本分别保存 · 图表数据见chart-data.json · 无外部资源和联网请求</footer></div><script>'+script+'</script></body></html>'
 (out/'research-report.html').write_text(page,encoding='utf-8')
 md='# '+title+'\n\n'+str(bundle.get('research_summary') or '依据本次实际记录生成；未核验材料保留状态。')+'\n\n## 史料矩阵\n\n'+markdown_table(sources,SOURCE_COLUMNS)+'\n## 文献矩阵\n\n'+markdown_table(lit,LIT_COLUMNS)+'\n## 命题矩阵\n\n'+markdown_table(claims,CLAIM_COLUMNS)+'\n## 图表\n\n![时间线](timeline.svg)\n\n![核验层级](verification.svg)\n\n![命题证据](claim-evidence.svg)\n'
 (out/'research-report.md').write_text(md,encoding='utf-8')
 return d

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--output-dir',required=True);p.add_argument('--title',default='历史史料研究矩阵');a=p.parse_args()
 try:build_report(json.loads(Path(a.input).read_text(encoding='utf-8')),Path(a.output_dir),title=a.title)
 except (ValueError,KeyError,TypeError) as e:p.exit(1,str(e)+'\n')
 except OSError as e:p.exit(2,str(e)+'\n')
if __name__=='__main__':main()
