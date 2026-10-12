"""Standard-library offline tools; structure validation does not prove authenticity."""
import csv, datetime, json, pathlib, re, string
from urllib.parse import urlparse
ROOT=pathlib.Path(__file__).resolve().parents[1]
def read_json(path):return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))
def blank_record():return read_json(ROOT/'assets/source-record-template.json')
def schema_check(v,s,path,errors):
 t=s.get('type');t=[t] if isinstance(t,str) else t
 checks={'string':lambda x:isinstance(x,str),'null':lambda x:x is None,'array':lambda x:isinstance(x,list),'object':lambda x:isinstance(x,dict),'boolean':lambda x:isinstance(x,bool)}
 if t and not any(checks[x](v) for x in t):errors.append(path+': wrong type');return
 if 'enum' in s and v not in s['enum']:errors.append(path+': invalid enum')
 if isinstance(v,str) and len(v)<s.get('minLength',0):errors.append(path+': empty')
 if isinstance(v,dict):
  for k in s.get('required',[]):
   if k not in v:errors.append(path+'.'+k+': missing')
  for k,x in v.items():
   if k in s.get('properties',{}):schema_check(x,s['properties'][k],path+'.'+k,errors)
   elif s.get('additionalProperties') is False:errors.append(path+'.'+k+': unknown field')
 if isinstance(v,list):
  if len(v)<s.get('minItems',0):errors.append(path+': empty list')
  for i,x in enumerate(v):schema_check(x,s.get('items',{}),f'{path}[{i}]',errors)
def valid_date(v):
 if not re.fullmatch(r'\d{4}(?:-\d{2})?(?:-\d{2})?',v):return False
 try:
  p=list(map(int,v.split('-')));earliest=datetime.date(*(p+[1]*(3-len(p))));return earliest<=datetime.date.today()
 except ValueError:return False
def valid_observation_time(value):
 """Observed date or timezone-aware ISO8601 timestamp; never a naive time."""
 if not isinstance(value,str):return False
 if re.fullmatch(r'\d{4}-\d{2}-\d{2}',value):return valid_date(value)
 if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})',value):return False
 try:
  observed=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
  return observed.tzinfo is not None and observed<=datetime.datetime.now(datetime.timezone.utc)
 except ValueError:return False

def checked_fields(r,methods=None):return {f for p in r.get('provenance_trail',[]) if isinstance(p,dict) and p.get('result')=='verified' and (not methods or p.get('method') in methods) for f in p.get('actually_checked',[])}
def validate(records):
 errors=[];seen=set();schema=read_json(ROOT/'assets/source-record.schema.json')
 if not isinstance(records,list):return ['root: expected array']
 for i,r in enumerate(records):
  prefix=f'record[{i}]';schema_check(r,schema,prefix,errors)
  if not isinstance(r,dict) or any(e.startswith(prefix+':') or e.startswith(prefix+'.') or e.startswith(prefix+'[') for e in errors):continue
  if r['record_id'] in seen:errors.append(prefix+': duplicate record_id')
  seen.add(r['record_id'])
  for k in ['document_date','publication_date','declassification_date','digitization_date','access_date']:
   if r.get(k) and not valid_date(r[k]):errors.append(prefix+'.'+k+': invalid/future date; preserve historical date in raw/calendar fields')
  for k in ['catalogue_url','fulltext_url','digital_image_url']:
   if r.get(k):
    try:
     u=urlparse(r[k]);valid=u.scheme in ['http','https'] and bool(u.hostname) and not any(c.isspace() for c in r[k]);u.port
    except ValueError:valid=False
    if not valid:errors.append(prefix+'.'+k+': invalid HTTP URL')
  for p in r['provenance_trail']:
   if not valid_observation_time(p['checked_at']):errors.append(prefix+': invalid provenance date')
   if any(f not in schema['properties'] and (not f.startswith('publication.') or f[12:] not in schema['properties']['publication']['properties']) for f in p['actually_checked']):errors.append(prefix+': provenance unknown fields')
  if r.get('document_date') and valid_date(r['document_date']):
   creation=r['document_date'];cp=list(map(int,creation.split('-')));clow=datetime.date(*(cp+[1]*(3-len(cp))))
   for k in ['publication_date','declassification_date','digitization_date']:
    if r.get(k) and valid_date(r[k]):
     lp=list(map(int,r[k].split('-')));year=lp[0];month=lp[1] if len(lp)>1 else 12
     import calendar
     lhigh=datetime.date(year,month,lp[2] if len(lp)>2 else calendar.monthrange(year,month)[1])
     if lhigh<clow:errors.append(prefix+'.'+k+': precedes document creation')
  covered=checked_fields(r)
  if r['metadata_verification_status']=='verified' and (not r['document_title_original'] or 'document_title_original' not in covered):errors.append(prefix+': verified metadata lacks matching provenance')
  if any(f not in covered for f in r['verified_fields']):errors.append(prefix+': verified_fields lacks provenance')
  methods={'image_verified':{'image'},'fulltext_verified':{'image','fulltext','edition'}}.get(r['content_verification_status'])
  if methods and not body_verified(r,methods):errors.append(prefix+': content verification lacks provenance')
  if r['document_access_status'] in ['catalogue_only','search_only','offline','denied','unavailable'] and methods:errors.append(prefix+': access/content conflict')
  if r['content_verification_status']=='image_verified' and r['document_access_status']!='image':errors.append(prefix+': image verification requires image access')
  if r['excerpt_verification_status'] in ['image_verified','fulltext_verified'] and not r['original_text_excerpt']:errors.append(prefix+': verified excerpt missing text')
  if r['excerpt_verification_status']=='image_verified' and r['document_access_status']!='image':errors.append(prefix+': image excerpt requires image access')
  if r['original_text_excerpt']:
   if r['excerpt_verification_status'] in ['none',None]:errors.append(prefix+': quote requires explicit verification status')
   if not r['excerpt_location']:errors.append(prefix+': excerpt lacks location')
   if r['document_access_status'] not in ['image','fulltext']:errors.append(prefix+': inaccessible content cannot have excerpt')
   em={'image_verified':{'image'},'fulltext_verified':{'image','fulltext','edition'}}.get(r['excerpt_verification_status'])
   if em and not {'original_text_excerpt','excerpt_location'}<=checked_fields(r,em):errors.append(prefix+': excerpt lacks matching provenance')
  if r['excerpt_translation'] and not r['original_text_excerpt']:errors.append(prefix+': translation lacks original')
  support={e['claim_id'] for e in r['claim_evidence'] if e['stance'] in ['support','partial']};against={e['claim_id'] for e in r['claim_evidence'] if e['stance']=='contradict'}
  if set(r['supported_claims'])!=support or set(r['contradictory_claims'])!=against:errors.append(prefix+': claim lists disagree with claim_evidence')
  if r['is_simulation'] and (r['metadata_verification_status']=='verified' or r['content_verification_status'] in ['image_verified','fulltext_verified'] or r['excerpt_verification_status'] in ['image_verified','fulltext_verified'] or any(p['result']=='verified' for p in r['provenance_trail'])):errors.append(prefix+': fictional/simulation record cannot carry real verified status')
  if r['is_simulation'] and r['citation'] and r['citation'].get('status')=='complete':errors.append(prefix+': simulation cannot be real citation')
  if r['citation'] and r['citation'].get('status')=='complete' and citation(r)['status']!='complete':errors.append(prefix+': complete citation lacks verified fields')
 return errors

def body_verified(r,methods={'image','fulltext','edition'}):
 fields=checked_fields(r,methods)
 return bool(('body_content_verified' in fields and r.get('body_content_verified')) or ('fulltext_url' in fields and r.get('fulltext_url')) or ('original_text_excerpt' in fields and r.get('original_text_excerpt')))

def relationships(rows):
 groups={};relations=[]
 for r in rows:
  key=r.get('original_identity') or (str((r['original_repository'],r['archive_reference'])) if r.get('original_repository') and r.get('archive_reference') else 'record:'+r['record_id'])
  groups.setdefault(key,[]).append(r)
 output=[]
 for key,items in groups.items():
  output.append({'identity':key,'record_ids':[r['record_id'] for r in items],'independent_source_count':1 if all(x.get('original_identity')==key for x in items) else None,'review_required':True})
  for a,b in zip(items,items[1:]):relations.append({'left':a['record_id'],'right':b['record_id'],'relation':'version_of' if a.get('original_identity') and a.get('original_identity')==b.get('original_identity') and (a.get('version_kind')!=b.get('version_kind') or a.get('edition_identifier')!=b.get('edition_identifier')) else 'possible_duplicate','basis':'explicit identity or repository/archive_reference','review_required':True})
 for i,a in enumerate(rows):
  for b in rows[i+1:]:
   if a.get('catalogue_url') and a['catalogue_url']==b.get('catalogue_url') and not any(x['left']==a['record_id'] and x['right']==b['record_id'] for x in relations):relations.append({'left':a['record_id'],'right':b['record_id'],'relation':'possible_duplicate','basis':'same catalogue URL','review_required':True})
 return {'groups':output,'relations':relations,'deleted_records':0}

def citation(r,style='zh',custom=None):
 if r.get('is_simulation'):return {'status':'simulation','reason':'模拟资料，不可用于正式引注'}
 if style not in ['zh','chicago','custom']:raise ValueError('unsupported style')
 covered=checked_fields(r);p={k:v for k,v in (r.get('publication') or {}).items() if 'publication.'+k in covered};cat=r.get('source_category');req=['document_title_original','document_date']
 if r.get('document_access_status')=='catalogue_only' or r.get('content_verification_status')=='metadata_only':return {'status':'catalogue_record','reason':'仅目录／元数据已核验，不是正文证据引注','catalogue_url':r.get('catalogue_url') if 'catalogue_url' in covered else None}
 if r.get('content_verification_status') not in ['image_verified','fulltext_verified'] or not body_verified(r):return {'status':'incomplete','reason':'引注待完善：尚未核验文件正文'}
 if p.get('un_symbol'):req+=['publication.un_symbol']
 elif cat=='edited_primary':
  req+=['publication.title','publication.editor','publication.publisher','publication.year']
  req+=['publication.page'] if p.get('page') else ['publication.document_number','publication.locator']
 elif cat=='contemporary_public' and p.get('newspaper'):req+=['publication.newspaper','publication.issue_date','publication.page']
 else:req+=['original_repository','archive_reference','original_page_or_folio']
 def get(k):return p.get(k.split('.')[1]) if k.startswith('publication.') else r.get(k)
 missing=[k for k in req if not get(k) or k not in covered]
 if (r.get('catalogue_url') or r.get('fulltext_url')) and ('access_date' not in covered or not r.get('access_date')):missing.append('access_date')
 if r.get('metadata_verification_status')!='verified':missing.append('metadata_verification_status verified')
 if missing:return {'status':'incomplete','reason':'引注待完善：缺失或未核验 '+', '.join(missing),'missing_fields':missing}
 title=r['document_title_original'];date=r['document_date'];author=r.get('creator') if 'creator' in covered else None
 def page_label(value,pdf=False):
  if not value:return None
  value=str(value)
  if re.search(r'页|葉|叶|fol\.|folio|pp?\.',value,re.I):return ('PDF'+value if pdf and not value.startswith('PDF') else value)
  return ('PDF第' if pdf else '第')+value+'页'
 loc=p.get('page') or p.get('locator') if cat=='edited_primary' or p.get('newspaper') else r.get('original_page_or_folio') if 'original_page_or_folio' in covered else None
 zloc=page_label(loc) if (cat!='edited_primary' or p.get('page')) else loc
 if p.get('un_symbol'):
  # UN document locator never borrows an unrelated original folio field.
  loc=', '.join(x for x in [p.get('page'),p.get('locator'),('PDF p. '+r['pdf_page']) if 'pdf_page' in covered and r.get('pdf_page') else None] if x) or None
  zloc='，'.join(x for x in [page_label(p.get('page')),p.get('locator'),page_label(r['pdf_page'],True) if 'pdf_page' in covered and r.get('pdf_page') else None] if x) or None
 docnum=(', doc. '+p['document_number']) if p.get('document_number') else ''
 zdoc=('，第'+p['document_number']+'号文件') if p.get('document_number') else ''
 place=(p['place']+': ') if p.get('place') else ''
 zplace=(p['place']+'：') if p.get('place') else ''
 url=(r.get('catalogue_url') if 'catalogue_url' in covered else None) or (r.get('fulltext_url') if 'fulltext_url' in covered else None)
 suffix=f', {url}, accessed {r["access_date"]}' if url and r.get('access_date') else ''
 if style=='custom':
  if not custom:return {'status':'incomplete','reason':'用户期刊体例须人工适配或提供 declarative templates'}
  values={k:str(v) for k,v in r.items() if k in covered and v not in [None,''] and not isinstance(v,(dict,list))};values.update({f'publication_{k}':str(v) for k,v in p.items() if v not in [None,'']})
  try:
   result={}
   for k in ['first_note','short_note','bibliography']:
    template=custom[k]
    for _,field,fmt,conv in string.Formatter().parse(template):
     if field is not None and (field not in values or fmt or conv):raise ValueError('unverified, empty or unsupported placeholder '+str(field))
    result[k]=template.format_map(values)
    if not result[k].strip():raise ValueError('empty rendered citation')
   return dict(status='complete',**result)
  except (KeyError,ValueError,TypeError) as e:return {'status':'incomplete','reason':'自定义体例待完善 '+str(e)}
 prefix=(author+', ') if author else ''
 if p.get('un_symbol'):
  first=f'{prefix}"{title}," {date}, {p["un_symbol"]}'+(', '+loc if loc else '');bib=f'{p["un_symbol"]}. "{title}." {date}';short=f'{p["un_symbol"]}, {loc or date}'
 elif cat=='edited_primary':
  volume=', vol. '+p['volume'] if p.get('volume') else ''
  first=f'{prefix}"{title}," {date}, in *{p["title"]}*{volume}, ed. {p["editor"]} ({place}{p["publisher"]}, {p["year"]}){docnum}, {loc}'
  bib=f'{p["editor"]}, ed. *{p["title"]}*{volume}. {place}{p["publisher"]}, {p["year"]}'
  short=f'"{title}," *{p["title"]}*{volume}{docnum}, {loc}'
 elif cat=='contemporary_public' and p.get('newspaper'):
  first=f'{prefix}"{title}," *{p["newspaper"]}*, {p["issue_date"]}, {loc}';bib=f'{p["newspaper"]}. "{title}." {p["issue_date"]}';short=f'"{title}," {loc}'
 else:
  chain=', '.join(str(r[k]) for k in ['original_repository','fonds_or_collection','series','file_unit','archive_reference'] if k in covered and r.get(k))
  first=f'{prefix}"{title}," {date}, {chain}, {loc}';bib=f'{r["original_repository"]}. {chain}. "{title}." {date}';short=f'"{title}," {loc}'
 if style=='zh':
  titlebit=(author+'，' if author else '')+'《'+title+'》'
  if cat=='edited_primary' and not p.get('un_symbol'):
   vol='，'+p['volume'] if p.get('volume') else ''
   first=f'{titlebit}，{date}，载{p["editor"]}编：《{p["title"]}》{vol}，{zplace}{p["publisher"]}，{p["year"]}年{zdoc}，{zloc}'
   bib=f'{p["editor"]}编：《{p["title"]}》{vol}，{zplace}{p["publisher"]}，{p["year"]}年'
  elif p.get('newspaper'):first=f'{titlebit}，《{p["newspaper"]}》，{p["issue_date"]}，{zloc}';bib=f'《{p["newspaper"]}》，{p["issue_date"]}，{zloc}'
  elif p.get('un_symbol'):first=f'{titlebit}，{date}，联合国文件{p["un_symbol"]}'+('，'+zloc if zloc else '');bib=f'联合国文件{p["un_symbol"]}：《{title}》，{date}'
  else:first=f'{titlebit}，{date}，{chain.replace(", ","，")}，{zloc}';bib=f'{r["original_repository"]}藏，{chain.replace(", ","，")}'
  if cat=='edited_primary' and not p.get('un_symbol'):short=f'《{title}》，《{p["title"]}》'+('，'+p['volume'] if p.get('volume') else '')+zdoc+'，'+str(zloc)
  elif p.get('un_symbol'):short=p['un_symbol']+('，'+zloc if zloc else '')
  else:short=f'《{title}》，{zloc or date}'
  zsuffix=f'，{url}，访问日期{r["access_date"]}' if url and r.get('access_date') else ''
  return {'status':'complete','first_note':first+zsuffix+'。','short_note':short+'。','bibliography':bib+zsuffix+'。','note':'正文已核验的引注草稿；格式须依目标期刊复核，结构验证不证明真实性'}
 return {'status':'complete','first_note':first+suffix+'.','short_note':short+'.','bibliography':bib+suffix+'.','note':'Chicago 引注草稿；人名排序及馆藏特殊格式须人工复核'}

def cell(v):
 s=json.dumps(v,ensure_ascii=False,separators=(',',':')) if isinstance(v,(dict,list)) else '' if v is None else str(v)
 return "'"+s if s.lstrip().startswith(('=','+','-','@','\t','\r')) else s

def write_exports(name,rows,out):
 (out/f'{name}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');fields=list(dict.fromkeys(k for r in rows for k in r))
 with (out/f'{name}.csv').open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:cell(v) for k,v in r.items()} for r in rows)
 def md(v):return str(v).replace('|','\\|').replace('\n','<br>')
 text='| '+' | '.join(fields)+' |\n| '+' | '.join('---' for _ in fields)+' |\n' if fields else '无记录。\n';text+=''.join('| '+' | '.join(md(cell(r.get(k))) for k in fields)+' |\n' for r in rows)
 (out/f'{name}.md').write_text(text,encoding='utf-8')
def export_bundle(bundle,out,style='zh',custom=None,include_report=True):
 if not isinstance(bundle,dict) or 'sources' not in bundle:raise ValueError('bundle requires sources')
 rows=bundle['sources'];errors=validate(rows)
 for name in ['search_log','claims']:
  if not isinstance(bundle.get(name,[]),list) or any(not isinstance(x,dict) for x in bundle.get(name,[])):errors.append(name+': expected array of objects')
 for entry in bundle.get('search_log',[]):
  if not isinstance(entry,dict):continue
  n=entry.get('observed_hits')
  if n is not None and (type(n) is not int or n<0):errors.append('search_log: observed_hits must be observed nonnegative integer or null')
  if entry.get('searched_at') and not valid_observation_time(entry['searched_at']):errors.append('search_log: invalid searched_at')
  status=entry.get('status')
  allowed={'success','completed','partial','planned','offline','failed','failure','denied','unavailable','unknown'}
  if status is not None and (not isinstance(status,str) or status not in allowed):errors.append('search_log: invalid status')
  if n is not None and status not in {'success','completed','partial'}:errors.append('search_log: unexecuted/failed operation cannot record hits')
  for field in ['query','database','operation','limitations','provenance_locator']:
   if entry.get(field) is not None and not isinstance(entry[field],str):errors.append('search_log: '+field+' must be string or null')
  if entry.get('record_ids') is not None and (not isinstance(entry['record_ids'],list) or any(not isinstance(x,str) for x in entry['record_ids'])):errors.append('search_log: record_ids must be string array')
  if status in {'planned','offline','failed','failure','denied','unavailable'} and entry.get('operation_success') is True:errors.append('search_log: failed/unexecuted operation cannot claim success')
  if 'operation_success' in entry and type(entry['operation_success']) is not bool:errors.append('search_log: operation_success must be boolean')
 for c in bundle.get('claims',[]):
  if not isinstance(c,dict):continue
  if not isinstance(c.get('claim_id'),str) or not c['claim_id']:errors.append('claims: missing claim_id')
 ids=[c.get('claim_id') for c in bundle.get('claims',[]) if isinstance(c,dict)]
 if len(ids)!=len(set(ids)):errors.append('claims: duplicate claim_id')
 for c in bundle.get('claims',[]):
  if isinstance(c,dict) and (not isinstance(c.get('text'),str) or not c['text'].strip()):errors.append('claims: nonempty text required')
 for r in rows:
  for e in r.get('claim_evidence',[]):
   if e['claim_id'] not in ids:errors.append('claim_evidence: unknown bundle claim_id '+e['claim_id'])
 if errors:raise ValueError('\n'.join(errors))
 from research_report import validate_literature
 validate_literature(bundle)
 out.mkdir(parents=True,exist_ok=True);write_exports('sources',rows,out);write_exports('search-log',bundle.get('search_log',[]),out)
 claims={c['claim_id']:c.get('text','') for c in bundle.get('claims',[])};matrix=[]
 for r in rows:
  for e in r['claim_evidence']:matrix.append(dict(e,claim_text=claims.get(e['claim_id'],''),record_id=r['record_id'],independence_group=r.get('independence_group') or r.get('original_identity')))
 write_exports('claim-evidence',matrix,out);write_exports('citations',[dict(record_id=r['record_id'],**citation(r,style,custom)) for r in rows],out)
 (out/'export-notes.txt').write_text('UTF-8。JSON 是无损权威导出。CSV 嵌套对象为 JSON，null 留空；疑似公式前加单引号防止表格执行。CSV 非无损往返格式，恢复原值使用 JSON。结构验证不证明史料真实性。\n',encoding='utf-8')
 if include_report:
  from research_report import build_report
  build_report(bundle,out,title=bundle.get('research_title','历史史料研究矩阵'),style=style,custom=custom,validated=True)
