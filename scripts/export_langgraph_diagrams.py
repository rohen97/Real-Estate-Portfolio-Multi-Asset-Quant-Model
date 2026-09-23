import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from packages.orchestration.langgraph_workflow import create_asset_graph,create_portfolio_graph
out=ROOT/'docs/architecture';out.mkdir(parents=True,exist_ok=True)
for name,graph in [('asset-decision-langgraph',create_asset_graph()),('portfolio-decision-langgraph',create_portfolio_graph())]:
 mermaid=graph.get_graph().draw_mermaid();path=out/(name+'.mmd');path.write_text(mermaid,encoding='utf-8');print(path)
