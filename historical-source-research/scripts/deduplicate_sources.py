#!/usr/bin/env python3
"""Suggest original/edition relations without deleting records. Exit 0 success, 1 invalid records, 2 input error."""
import argparse,json,pathlib,sys
from source_tools import read_json,relationships,validate

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--output');a=p.parse_args()
 try:
  data=read_json(a.input);rows=data['sources'] if isinstance(data,dict) else data;errors=validate(rows)
  if errors:print('\n'.join(errors),file=sys.stderr);return 1
  text=json.dumps(relationships(rows),ensure_ascii=False,indent=2)+'\n'
  if a.output:pathlib.Path(a.output).write_text(text,encoding='utf-8')
  else:print(text,end='')
  return 0
 except (OSError,ValueError,TypeError,KeyError) as e:print(str(e),file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
