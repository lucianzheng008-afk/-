#!/usr/bin/env python3
"""Export source catalogue, citations, research log and claim matrix as UTF-8 JSON/CSV/Markdown. Exit 0 success, 1 invalid data, 2 input error."""
import argparse,pathlib,sys
from source_tools import read_json,export_bundle,validate

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',help='JSON array or {sources, search_log, claims} bundle');p.add_argument('--output-dir',required=True);p.add_argument('--style',choices=['zh','chicago','custom'],default='zh');p.add_argument('--citation-template',help='JSON object with first_note, short_note, bibliography format strings');a=p.parse_args()
 try:
  data=read_json(a.input);custom=read_json(a.citation_template) if a.citation_template else None
 except (OSError,ValueError) as e:print(str(e),file=sys.stderr);return 2
 bundle={'sources':data} if isinstance(data,list) else data
 try:
  export_bundle(bundle,pathlib.Path(a.output_dir),a.style,custom);return 0
 except (ValueError,TypeError,KeyError) as e:print(str(e),file=sys.stderr);return 1
 except OSError as e:print(str(e),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
