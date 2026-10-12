#!/usr/bin/env python3
"""Exit 0 valid structure, 1 validation errors, 2 input/usage error."""
import argparse,json,sys
from source_tools import read_json,validate

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',help='JSON source array or bundle containing sources');a=p.parse_args()
 try:
  value=read_json(a.input);errors=validate(value['sources'] if isinstance(value,dict) else value)
 except (OSError,ValueError,TypeError,KeyError) as e:print(str(e),file=sys.stderr);return 2
 print(json.dumps({'structurally_valid':not errors,'authenticity_verified':False,'errors':errors},ensure_ascii=False,indent=2));return 1 if errors else 0
if __name__=='__main__':sys.exit(main())
