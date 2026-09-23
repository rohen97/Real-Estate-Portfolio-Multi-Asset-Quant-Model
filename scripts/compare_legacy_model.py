import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.legacy.comparison import compare
pilot=ROOT/'data/pilot';legacy=json.loads((pilot/'legacy_inputs.json').read_text());results=json.loads((ROOT/'data/processed/full_model_results.json').read_text());outcomes=json.loads((pilot/'outcomes.json').read_text());rows=compare(legacy,results,outcomes);target=ROOT/'data/processed/legacy_comparison.json';target.write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps({'assets':len(rows),'corrected_vs_economic_agreement':sum(x['legacy_vs_economic_agreement'] for x in rows),'published_calculation_differences':sum(x.get('published_current') is not None and (abs(x['published_current']-x['corrected_current'])>.01 or abs(x['published_future']-x['corrected_future'])>.01) for x in rows)},indent=2))
