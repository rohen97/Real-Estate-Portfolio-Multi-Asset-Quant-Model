import sys,argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.data.underwriting_import import import_underwriting
p=argparse.ArgumentParser();p.add_argument('--workbook',required=True);p.add_argument('--strict',action='store_true');p.add_argument('--rebuild',action='store_true');a=p.parse_args();report=import_underwriting(Path(a.workbook),ROOT/'data/processed/portfolio.json',ROOT/'data/observed');print(json.dumps({'assets_total':report['assets_total'],'assets_ready':report['assets_ready'],'error_records':len(report['errors']),'warning_records':len(report['warnings'])},indent=2));
if a.strict and report['errors']:raise SystemExit(2)
if a.rebuild:subprocess.run([str(ROOT/'tools/uv.exe'),'run','python',str(ROOT/'scripts/build_full_model.py')],cwd=ROOT,check=True)
