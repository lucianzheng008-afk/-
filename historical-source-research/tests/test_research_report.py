import csv,json,sys,tempfile,unittest,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from source_tools import blank_record
from research_report import build_report,chart_data

def fixture():
 r=blank_record();r.update(record_id='S1',document_title_original='未读原文的目录',source_category='finding_aid',document_access_status='catalogue_only',content_verification_status='metadata_only',document_date='1925-11',document_date_precision='month')
 r['claim_evidence']=[{'claim_id':'C1','stance':'undetermined','proof_value':'undetermined','basis':'只有目录'}]
 return {'sources':[r],'claims':[{'claim_id':'C1','text':'命题一'},{'claim_id':'C2','text':'无材料命题'}],'search_log':[],'literature':[{'literature_id':'L1','title':'研究文献','author':'Author','year':'2000','publication':'Journal','research_question':'问题','method':None,'findings':None,'primary_source_leads':[],'verification_status':'metadata_only','url':'https://example.org/paper','claim_ids':['C1'],'notes':'未读全文'}]}
class Reports(unittest.TestCase):
 def test_all_claims_include_unobserved_gaps(self):
  d=chart_data(fixture());self.assertEqual([c['claim_id'] for c in d['claims']],['C1','C2']);self.assertEqual(d['claims'][1]['evidence'],[])
 def test_timeline_preserves_month_precision_and_excludes_unknown(self):
  b=fixture();r=blank_record();r['record_id']='S2';b['sources'].append(r)
  d=chart_data(b);self.assertEqual(len(d['timeline']),1);self.assertEqual(d['timeline'][0]['date'],'1925-11');self.assertEqual(d['undated'],['S2'])
 def test_report_artifacts_and_readable_matrix(self):
  with tempfile.TemporaryDirectory() as t:
   build_report(fixture(),Path(t),title='研究示例')
   for n in ['research-report.html','source-matrix.csv','literature-matrix.csv','claim-matrix.csv','timeline.svg','verification.svg','claim-evidence.svg','chart-data.json','research-report.md']:
    self.assertTrue((Path(t)/n).is_file(),n)
   with (Path(t)/'source-matrix.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
   self.assertEqual(rows[0]['编号'],'S1');self.assertIn('内容核验',rows[0]);self.assertNotIn('provenance_trail',rows[0])
   for n in ['timeline.svg','verification.svg','claim-evidence.svg']:ET.parse(Path(t)/n)
 def test_untrusted_html_never_executable(self):
  b=fixture();b['sources'][0]['document_title_original']='</script><script>alert(1)</script>';b['literature'][0]['title']='<img src=x onerror=alert(1)>'
  with tempfile.TemporaryDirectory() as t:
   build_report(b,Path(t));text=(Path(t)/'research-report.html').read_text()
   self.assertNotIn('</script><script>alert(1)</script>',text);self.assertNotIn('<img src=x',text);self.assertEqual(text.count('<script>'),1)
 def test_literature_unsafe_url_and_duplicate_rejected(self):
  b=fixture();b['literature'][0]['url']='javascript:alert(1)'
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):build_report(b,Path(t))
  b=fixture();b['literature'].append(dict(b['literature'][0]))
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):build_report(b,Path(t))
 def test_literature_metadata_only_cannot_claim_fulltext_findings(self):
  b=fixture();b['literature'][0]['findings']='已阅读全文发现'
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):build_report(b,Path(t))
 def test_empty_report_no_invented_sources(self):
  with tempfile.TemporaryDirectory() as t:
   b={'sources':[],'claims':[],'search_log':[]};build_report(b,Path(t));d=json.loads((Path(t)/'chart-data.json').read_text());self.assertEqual(d['source_count'],0)
 def test_literature_no_archive_counts(self):
  d=chart_data(fixture());self.assertEqual(d['source_count'],1);self.assertEqual(d['literature_count'],1)
 def test_export_pipeline_generates_visuals_by_default(self):
  from source_tools import export_bundle
  with tempfile.TemporaryDirectory() as t:
   export_bundle(fixture(),Path(t));self.assertTrue((Path(t)/'research-report.html').exists())
if __name__=='__main__':unittest.main()
