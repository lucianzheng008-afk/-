"""Portable package invariants; no network or optional dependencies."""
import json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from source_tools import blank_record,validate,schema_check
class PackageTests(unittest.TestCase):
 def test_local_markdown_links_resolve_inside_package(self):
  for p in [ROOT/'SKILL.md',*sorted((ROOT/'references').glob('*.md'))]:
   for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
    if '://' in target or target.startswith('#'):continue
    resolved=(p.parent/target.split('#')[0]).resolve()
    self.assertTrue(resolved.is_relative_to(ROOT),str(p)+': '+target)
    self.assertTrue(resolved.is_file(),str(p)+': '+target)
 def test_schema_template_same_fields(self):
  schema=json.loads((ROOT/'assets/source-record.schema.json').read_text())
  r=blank_record();r['record_id']='TEST-EMPTY'
  self.assertEqual(set(schema['required']),set(r))
  self.assertEqual(set(schema['properties']),set(r))
  self.assertEqual(validate([r]),[])
 def test_frontmatter_identity_nonempty(self):
  text=(ROOT/'SKILL.md').read_text(encoding='utf-8')
  fm=re.match(r'^---\n(.*?)\n---',text,re.S).group(1)
  self.assertIn('name: '+ROOT.name,fm)
  self.assertRegex(fm,r'(?m)^description: .+')
  self.assertNotIn('[TODO:',text)
 def test_ui_interface_required_user_values(self):
  text=(ROOT/'agents/openai.yaml').read_text(encoding='utf-8')
  self.assertIn('display_name: "Historical Source Researcher"',text)
  self.assertIn('$historical-source-research',text)
  self.assertNotIn('allow_implicit_invocation: false',text)
if __name__=='__main__':unittest.main()
