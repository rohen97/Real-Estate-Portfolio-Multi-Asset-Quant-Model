import Plot from 'react-plotly.js';

// Plotly 4 expects title objects; older string titles silently disappear.
function titleObjects(value: any): any {
  if (Array.isArray(value)) return value.map(titleObjects);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.entries(value).map(([key, item]) => [key,
    key === 'title' && typeof item === 'string' ? {text: item} : titleObjects(item),
  ]));
}

export default function PlotlyChart({data,layout,ariaLabel}:{data:any[];layout:any;ariaLabel:string}) {
  return <div className="chart" role="img" aria-label={ariaLabel}><Plot data={data}
    layout={{autosize:true,paper_bgcolor:'#fff',plot_bgcolor:'#fff',font:{family:'IBM Plex Sans, Arial',color:'#161616',size:11},margin:{l:60,r:25,t:60,b:65},...titleObjects(layout)}}
    config={{responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d','select2d']}}
    style={{width:'100%',height:'100%'}} useResizeHandler/></div>;
}
