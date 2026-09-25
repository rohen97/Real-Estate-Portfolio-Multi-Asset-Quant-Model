"""Create an editable client presentation with a dedicated zoning decision section."""
from pathlib import Path
import json, math, hashlib
from collections import Counter
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION, XL_TICK_MARK, XL_TICK_LABEL_POSITION
from pptx.chart.data import CategoryChartData
from pptx.oxml.xmlchemy import OxmlElement

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
SNAP = REPO/'public/data/api_snapshot.json'
ROUTES = json.loads(SNAP.read_text(encoding='utf-8'))['routes']
DATA = json.loads((OUT/'analysis/decision_data.json').read_text(encoding='utf-8'))
P = Presentation(); P.slide_width=Inches(13.333333); P.slide_height=Inches(7.5)
P.core_properties.title='Real Estate Portfolio Intelligence | Client Demonstration'
P.core_properties.subject='Asset economics, portfolio decisions and an explainable dashboard'
P.core_properties.author='Portfolio Intelligence'
P.core_properties.keywords='real estate; portfolio; valuation; dashboard; client demonstration'
BLUE='0F62FE'; DARK='202A38'; GRAY='5B6573'; PALE='EDF5FF'; LINE='D7E0EA'; TEAL='008578'; AMBER='995910'; GOLD='D58A28'; WHITE='FFFFFF'; RED='C63D45'
FONT='IBM Plex Sans'; LIGHT='IBM Plex Sans Light'; MED='IBM Plex Sans'
META=[]
def rgb(c):return RGBColor.from_string(c)
def rect(s,x,y,w,h,fill=WHITE,line=None,radius=False,lw=1):
    z=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius:z.adjustments[0]=.06
    z.fill.solid();z.fill.fore_color.rgb=rgb(fill)
    if line:z.line.color.rgb=rgb(line);z.line.width=Pt(lw)
    else:z.line.fill.background()
    return z
def txt(s,x,y,w,h,text,size=18,color=DARK,font=FONT,bold=False,align=PP_ALIGN.LEFT,margin=0):
    z=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));t=z.text_frame;t.clear();t.word_wrap=True
    t.margin_left=t.margin_right=Inches(margin);t.margin_top=t.margin_bottom=0
    for i,line in enumerate(str(text).split('\n')):
        q=t.paragraphs[0] if i==0 else t.add_paragraph();q.text=line;q.alignment=align;q.space_after=Pt(4)
        q.font.name=font;q.font.size=Pt(size);q.font.bold=bold;q.font.color.rgb=rgb(color)
        q.line_spacing=1.08
        for run in q.runs:
            run.font.name=font;run.font.size=Pt(size);run.font.bold=bold;run.font.color.rgb=rgb(color)
    return z
def line(s,x1,y1,x2,y2,color=LINE,width=1.1,arrow=False,dashed=False):
    z=s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1),Inches(y1),Inches(x2),Inches(y2));z.line.color.rgb=rgb(color);z.line.width=Pt(width)
    if arrow:
        e=OxmlElement('a:tailEnd');e.set('type','triangle');e.set('w','sm');e.set('len','sm');z.line._get_or_add_ln().append(e)
    if dashed:
        from pptx.enum.dml import MSO_LINE_DASH_STYLE
        z.line.dash_style=MSO_LINE_DASH_STYLE.DASH
    return z
def circle(s,x,y,d,fill=BLUE,line_color=None):
    z=s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x),Inches(y),Inches(d),Inches(d));z.fill.solid();z.fill.fore_color.rgb=rgb(fill)
    if line_color:z.line.color.rgb=rgb(line_color)
    else:z.line.fill.background()
    return z
def pill(s,x,y,w,text,color=BLUE,fill=PALE):
    rect(s,x,y,w,.30,fill);txt(s,x+.10,y+.055,w-.2,.21,text,10.5,color,MED)
def slide(title,subtitle='',section='CLIENT DEMONSTRATION',source='',notes=''):
    s=P.slides.add_slide(P.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=rgb(WHITE)
    txt(s,.5,.22,11.8,.23,section,10,BLUE,MED)
    txt(s,.5,.64,12.25,.78,title,30,DARK,LIGHT)
    if subtitle:txt(s,.52,1.42,12.0,.48,subtitle,15,GRAY)
    line(s,.5,1.99,12.83,1.99,BLUE,.9)
    line(s,.5,7.01,12.83,7.01,LINE,.6)
    txt(s,.51,7.10,11.5,.23,source or 'Real Estate Portfolio Intelligence  |  Client discussion  |  September 2026',9,GRAY)
    txt(s,12.35,7.08,.48,.25,f'{len(P.slides):02}',10,GRAY,align=PP_ALIGN.RIGHT)
    s.notes_slide.notes_text_frame.text=notes
    META.append({'slide':len(P.slides),'title':title,'source':source,'notes':notes})
    return s
def card(s,x,y,w,h,kicker,title,body='',color=BLUE):
    rect(s,x,y,w,h,PALE,LINE);rect(s,x,y,.04,h,color)
    txt(s,x+.2,y+.18,w-.4,.28,kicker,11,color,MED)
    txt(s,x+.2,y+.62,w-.4,.85,title,23,DARK,LIGHT)
    if body:txt(s,x+.2,y+1.65,w-.4,h-1.83,body,16,GRAY)
def takeaway(s,text,y=6.25,color=BLUE):
    rect(s,.5,y,12.33,.55,PALE);txt(s,.69,y+.13,11.94,.36,text,17,color,MED)
def metric(s,x,y,w,value,label,color=BLUE,small=''):
    txt(s,x,y,w,.70,value,36,color,LIGHT)
    txt(s,x,y+.83,w,.55,label,16,DARK)
    if small:txt(s,x,y+1.40,w,.55,small,12,GRAY)
def note(s,text,x=.5,y=6.78,w=12.1):txt(s,x,y,w,.20,text,9.5,GRAY)
def button(s,x,y,w,text,url):
    z=rect(s,x,y,w,.57,BLUE);z.click_action.hyperlink.address=url
    z=txt(s,x+.16,y+.14,w-.32,.32,text,16,WHITE,MED);z.click_action.hyperlink.address=url
def chart(s,x,y,w,h,categories,series,kind=XL_CHART_TYPE.COLUMN_CLUSTERED,colors=None,legend=False,ymin=None,ymax=None,major=None,fmt='0.0',labels=False):
    d=CategoryChartData();d.categories=categories
    for name,values in series:d.add_series(name,values)
    c=s.shapes.add_chart(kind,Inches(x),Inches(y),Inches(w),Inches(h),d).chart
    c.has_legend=legend;c.has_title=False
    if legend:c.legend.position=XL_LEGEND_POSITION.BOTTOM;c.legend.include_in_layout=False;c.legend.font.name=FONT;c.legend.font.size=Pt(12)
    c.chart_style=10
    for axis in [c.category_axis,c.value_axis]:
        axis.tick_labels.font.name=FONT;axis.tick_labels.font.size=Pt(12);axis.tick_labels.font.color.rgb=rgb(GRAY)
        axis.major_tick_mark=XL_TICK_MARK.NONE;axis.minor_tick_mark=XL_TICK_MARK.NONE
        axis.format.line.color.rgb=rgb(LINE)
    c.value_axis.has_major_gridlines=True;c.value_axis.major_gridlines.format.line.color.rgb=rgb(LINE)
    c.category_axis.tick_label_position=XL_TICK_LABEL_POSITION.LOW
    c.value_axis.major_gridlines.format.line.width=Pt(.5);c.value_axis.tick_labels.number_format=fmt
    if ymin is not None:c.value_axis.minimum_scale=ymin
    if ymax is not None:c.value_axis.maximum_scale=ymax
    if major is not None:c.value_axis.major_unit=major
    for i,ser in enumerate(c.series):
        color=(colors or [BLUE,TEAL,GOLD,GRAY])[i % len(colors or [BLUE,TEAL,GOLD,GRAY])]
        if kind==XL_CHART_TYPE.LINE:
            ser.format.line.color.rgb=rgb(color);ser.format.line.width=Pt(2.5)
        else:
            ser.format.fill.solid();ser.format.fill.fore_color.rgb=rgb(color);ser.format.line.fill.background()
            ser.invert_if_negative=False
    if labels:
        plot=c.plots[0];plot.has_data_labels=True;dl=plot.data_labels;dl.font.name=MED;dl.font.size=Pt(14);dl.font.color.rgb=rgb(DARK);dl.number_format=fmt
        dl.position=XL_LABEL_POSITION.OUTSIDE_END
    return c
def plot_axes(s,x,y,w,h,xmin,xmax,ymin,ymax,xticks,yticks,xlabel,ylabel):
    def px(v):return x+(v-xmin)/(xmax-xmin)*w
    def py(v):return y+h-(v-ymin)/(ymax-ymin)*h
    for v in yticks:
        line(s,x,py(v),x+w,py(v),LINE,.65)
        txt(s,x-.65,py(v)-.12,.5,.25,f'{v:g}',11,GRAY,align=PP_ALIGN.RIGHT)
    for v in xticks:
        txt(s,px(v)-.32,y+h+.1,.65,.3,f'{v:g}',11,GRAY,align=PP_ALIGN.CENTER)
    line(s,x,y+h,x+w,y+h,GRAY,.9);line(s,x,y,x,y+h,GRAY,.9)
    txt(s,x,y-.48,w,.32,ylabel,13,GRAY);txt(s,x,y+h+.40,w,.30,xlabel,13,GRAY,align=PP_ALIGN.CENTER)
    return px,py

core=ROUTES['/portfolio']['assets'];opt=ROUTES['/snapshots/optimise'];two=ROUTES['/snapshots/two-stage'];twins=ROUTES['/digital-twins/dashboard']
asset=core[0];adv=ROUTES['/assets/DEMO-001/advanced-analysis'];market=ROUTES['/market/public']
public_url='https://rohen97.github.io/Real-Estate-Portfolio-Multi-Asset-Quant-Model/'
fiction='Illustrative results from 10 fictional assets. SGD millions unless stated. Model snapshot: 25 September 2026.'

# 01 â€” restrained cover, with an original editable line-art motif.
s=P.slides.add_slide(P.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=rgb(WHITE)
rect(s,6.75,0,6.59,7.5,PALE)
txt(s,.58,.48,5.7,.3,'REAL ESTATE  /  CLIENT DEMONSTRATION',11,BLUE,MED)
txt(s,.58,2.23,6.10,1.65,'Portfolio\nintelligence',44,DARK,LIGHT)
txt(s,.62,4.16,5.35,1.02,'From asset assumptions\nto capital decisions',24,GRAY,LIGHT)
txt(s,.62,6.45,5.65,.48,'Model and dashboard demonstration\nSeptember 2026',13,GRAY)
for i in range(9):
    x=7.15+i*.19;y=1.05+i*.15;w=5.13-i*.29;h=5.54-i*.31
    z=rect(s,x,y,w,h,PALE,BLUE if i%3==0 else 'A6C8FF',radius=True,lw=1.4)
for i,(bx,bh) in enumerate([(8.45,1.5),(9.26,2.45),(10.07,1.94)]):
    rect(s,bx,5.7-bh,.62,bh,WHITE,BLUE,False,1.3)
    for j in range(int(bh/.34)-1):line(s,bx+.13,5.52-j*.31,bx+.48,5.52-j*.31,'A6C8FF',1)
s.notes_slide.notes_text_frame.text='Client presentation inspired only by slides 1â€“18 of the supplied POC PDF. Original branding and diagrams. Demonstration capability is implemented; asset underwriting is fictional, and investment alpha is unvalidated.'
META.append({'slide':1,'title':'Portfolio intelligence','source':'Supplied style reference, pages 1â€“18 only','notes':s.notes_slide.notes_text_frame.text})

# 02 â€” investment committee questions, not a feature inventory.
s=slide('Make the capital decision with a clearer view', 'Connect asset economics, portfolio constraints and the evidence behind each recommendation.', '01  /  THE CLIENT OPPORTUNITY')
card(s,.5,2.35,3.88,3.43,'ASSET STRATEGY','Which action\ncreates value?','Compare Hold, Retrofit, Repurpose, Redevelop and Sell on a common basis.')
card(s,4.72,2.35,3.88,3.43,'PORTFOLIO STRATEGY','Which plan fits\nthe mandate?','Balance capital release, retained income, project capacity and downside risk.')
card(s,8.94,2.35,3.88,3.43,'DECISION GOVERNANCE','What must be\nverified first?','Surface missing evidence and explain why a candidate needs further review.')
takeaway(s,'A practical output: a ranked, constrained and explainable decision brief.')
s.notes_slide.notes_text_frame.text='The client value proposition is an integrated review workflow. No measured productivity saving or financial uplift is claimed. Five implemented action types are Hold, Retrofit, Repurpose, Redevelop and Sell.'

# 03 â€” current-state friction, expressed as common challenges.
s=slide('The challenge is connecting evidence to a decision', 'Common portfolio review challenges â€” to be confirmed against the clientâ€™s current process.', '01  /  CURRENT UNDERSTANDING')
for i,(a,b,c) in enumerate([
 ('Fragmented evidence','Leases, title, planning and costs','Different owners and update cycles'),
 ('Inconsistent economics','Different time horizons and baselines','Gross value can be confused with incremental gain'),
 ('Competing objectives','Asset returns, income and liquidity','A strong asset idea may not fit the portfolio')]):
    y=2.36+i*1.33;circle(s,.56,y+.06,.40,BLUE);txt(s,.60,y+.115,.32,.24,str(i+1),13,WHITE,MED,align=PP_ALIGN.CENTER)
    txt(s,1.15,y,4.1,.41,a,23,DARK,LIGHT);txt(s,1.15,y+.49,4.38,.42,b,15,GRAY)
    line(s,5.9,y+.43,6.65,y+.43,BLUE,1.25,True);txt(s,7.02,y+.09,5.55,.82,c,23,DARK,LIGHT)
takeaway(s,'The platform makes assumptions comparable before it ranks the alternatives.')
s.notes_slide.notes_text_frame.text='These are common portfolio-review challenges, not findings about a specific prospective client. Ask how leases, costs and planning records are currently reconciled, whether asset proposals share a baseline, and how portfolio income and liquidity constraints enter the decision. The model offers a consistent comparison process; quantify any time saving during the pilot rather than assuming one.'

# 04 â€” input / modelling / decision chain.
s=slide('One workflow from inputs to investment review', 'Each stage produces an output that can be checked before the next decision.', '02  /  PROOF-OF-CONCEPT SCOPE')
stages=[('01','Assemble','Asset and\nmarket inputs'),('02','Validate','Dates, units\nand evidence'),('03','Compare','Cash flows\nand scenarios'),('04','Allocate','Capital, risk\nand income'),('05','Review','Decision brief\nand open gaps')]
for i,(n,a,b) in enumerate(stages):
    x=.5+i*2.5;rect(s,x,2.8,2.28,2.25,PALE,LINE);txt(s,x+.18,3.03,1.9,.3,n,13,BLUE,MED);txt(s,x+.18,3.56,1.91,.4,a,23,DARK,LIGHT);txt(s,x+.18,4.15,1.91,.6,b,16,GRAY)
    if i<4:line(s,x+2.28,3.88,x+2.48,3.88,BLUE,1.3,True)
for x,n,label in [(.55,'10','fictional demo assets'),(4.75,'5','action alternatives'),(8.95,'15','dashboard sections')]:
    txt(s,x,5.47,1.0,.59,n,34,BLUE,LIGHT);txt(s,x+1.15,5.65,2.7,.5,label,16,GRAY)
note(s,'The public demonstration uses fictional assets; client deployment begins with verified client inputs.')
s.notes_slide.notes_text_frame.text='The implemented public demonstration contains 10 fictional assets, 5 action types and 15 dashboard sections. The stages are an explanation of the existing modelling workflow, not a claim that client-system integration or autonomous approvals are complete. Each stage can be inspected through the dashboard and detailed report. A real client pilot starts by validating asset-level source records.'

# 05 â€” editable dashboard summary, faithfully presenting actual outputs.
s=slide('The dashboard connects the overview to the asset case', 'A simplified, editable view of the implemented workspace; open the public dashboard for the full interface.', '03  /  DASHBOARD WALKTHROUGH',fiction)
rect(s,.5,2.24,12.33,4.37,'F7F9FC',LINE)
rect(s,.5,2.24,1.62,4.37,DARK)
txt(s,.68,2.46,1.26,.67,'PORTFOLIO\nINTELLIGENCE',11,WHITE,MED)
for i,label in enumerate(['Portfolio','Digital Twins','Asset & evidence','Development','Scenarios','Optimiser']):txt(s,.68,3.34+i*.45,1.26,.35,label,11,'FFFFFF' if i==5 else 'BCC8D7',MED if i==5 else FONT)
for x,val,label in [(2.36,'10','Assets in view'),(5.77,'70.1%','Income retained'),(9.18,'S$9.95m','Expected gain vs Hold')]:
    rect(s,x,2.52,3.39,1.03,WHITE,LINE);txt(s,x+.17,2.65,3.02,.48,val,27,BLUE,LIGHT);txt(s,x+.17,3.20,3.02,.25,label,11,GRAY)
for x,n,title,body in [(2.36,'01','Asset evidence','Trace economics,\nplanning and gaps.'),(5.77,'02','Action comparison','See value, timing\nand downside together.'),(9.18,'03','Portfolio plan','Inspect allocations\nand binding constraints.')]:
    rect(s,x,3.76,3.39,1.86,WHITE,LINE);pill(s,x+.17,3.95,.46,n);txt(s,x+.17,4.42,3.04,.4,title,19,DARK,MED);txt(s,x+.17,4.92,3.01,.57,body,15,GRAY)
pill(s,2.53,5.97,4.21,'READINESS: DATA REQUIRED / MONITOR',AMBER,'FFF3DF')
button(s,9.02,5.87,3.38,'Open public dashboard  â†’',public_url)
s.notes_slide.notes_text_frame.text='This is a presentation adaptation of the implemented dashboard, constructed entirely from editable shapes and text. It is not a screenshot or an additional product feature. The 70.0851% income retention and S$9.947621m incremental NPV refer to the saved core multi-period portfolio. All 10 assets require additional evidence. Public Pages serves saved results; new calculations require a connected backend.'

# 06 â€” official market context, native chart with embedded workbook.
s=slide('Market context sharpens the questions for each asset', 'Official sector histories provide a common external reference; leases and costs determine the asset case.', '03  /  INPUTS AND EVIDENCE', 'Source: official URA / JTC series via data.gov.sg; cached 25 September 2026. Latest observation: 2026 Q2.')
hist=[h for h in market['history'] if h['measure']=='price'];periods=sorted(set.intersection(*[{o['period'] for o in h['observations'] if o['period']>='2021-Q1'} for h in hist]))
series=[]
for segment,label in [('private_residential','Residential'),('office','Office'),('retail','Retail'),('industrial','Industrial')]:
    h=next(h for h in hist if h['segment']==segment);d={o['period']:o['index'] for o in h['observations']};series.append((label,[d[p]/d[periods[0]]*100 for p in periods]))
txt(s,.6,2.30,7.4,.35,'Singapore sector price indices  |  2021 Q1 = 100',16,DARK,MED)
c=chart(s,.49,2.82,8.0,3.19,[p.replace('-Q',' Q') if p.endswith('Q1') else '' for p in periods],series,XL_CHART_TYPE.LINE,[BLUE,TEAL,GOLD,'8A3FFC'],True,80,170,30,'0')
txt(s,.70,6.04,7.3,.20,'Office and retail indices cover the Central Region.',10,GRAY)
rect(s,8.94,2.43,3.88,3.64,PALE,LINE)
txt(s,9.17,2.68,3.41,.61,'Two evidence layers',23,DARK,LIGHT)
txt(s,9.17,3.47,3.37,.35,'PUBLIC CONTEXT',11,BLUE,MED);txt(s,9.17,3.93,3.31,.68,'Sector direction, dates\nand source provenance',18,DARK)
txt(s,9.17,4.85,3.37,.35,'CLIENT UNDERWRITING',11,TEAL,MED);txt(s,9.17,5.28,3.31,.68,'Lease income, title, costs\nand transaction evidence',18,DARK)
takeaway(s,'Divergent sector paths support differentiated assumptions â€” not a single growth rate.')
s.notes_slide.notes_text_frame.text='Official observations: '+ '\n'.join(h['source_url'] for h in hist)+'\nEvery plotted series has the same 2021-Q1 origin and common completed-quarter history. These are regional/national aggregate indices, not appraisals or asset-level forecasts. Downloaded histories may be revised and are not point-in-time investment backtest inputs.'

from zoning_slides import add_zoning_section
add_zoning_section(globals())

# Common counterfactual after the dedicated zoning section.
s=slide('Compare every action against the same Hold baseline', 'Incremental economics reveal what the proposed action adds after costs, timing and retained asset value.', '03  /  MODEL LOGIC',fiction)
actions=[('Hold','Retain income'),('Retrofit','Improve the asset'),('Repurpose','Change the use'),('Redevelop','Rebuild the site'),('Sell','Release capital')]
for i,(a,b) in enumerate(actions):
    x=.5+i*2.5;rect(s,x,2.46,2.28,1.27,PALE,LINE);txt(s,x+.18,2.70,1.94,.38,a,22,BLUE,LIGHT);txt(s,x+.18,3.23,1.94,.3,b,13,GRAY)
rect(s,.5,4.25,12.33,1.3,DARK)
txt(s,.80,4.59,11.73,.70,'Incremental value  =  Action NPV  âˆ’  Hold NPV',30,WHITE,LIGHT,align=PP_ALIGN.CENTER)
for x,a,b in [(.6,'Count the whole cost','Capex, downtime and disposal'),(4.77,'Model timing explicitly','Success, delay and failure'),(8.94,'Separate debt from value','Financing is not project profit')]:
    txt(s,x,5.94,3.66,.4,a,18,BLUE,MED);txt(s,x,6.43,3.66,.35,b,14,GRAY)
s.notes_slide.notes_text_frame.text='The common financial principle is action value less the value of retaining the same asset. Annual core and monthly development engines retain distinct assumptions and timing. Hold incremental value is zero by construction, which does not mean the property has no absolute risk. Core annual and monthly development outputs must not be interchanged. Model source: packages/actions/real_options.py, detailed_cashflow.py and packages/valuation/engine.py.'

# 08 â€” editable vector decision plot using the exact displayed scenarios.
s=slide('The action plot makes the trade-off visible', 'DEMO-001: a fictional mixed-use asset. Higher expected value and lower modelled tail loss are preferred.', '03  /  ASSET DECISION PLOT',fiction)
ar=asset['actions'];maxrisk=max(a['cvar_95_m'] for a in ar);minval=min(a['expected_npv_m'] for a in ar)
xmax=math.ceil(maxrisk/5)*5;ymin=math.floor(minval/5)*5;px,py=plot_axes(s,1.13,2.86,6.45,2.65,-1,xmax,ymin,7,[0,5,10,15] if xmax<=20 else list(range(0,xmax+1,10)),list(range(int(ymin),6,5)),'95% tail loss / CVaR (S$m) â†’','Expected incremental NPV (S$m) â†‘')
line(s,1.13,py(0),7.58,py(0),'8E9CAB',1.2,dashed=True)
offset={'Hold':(.14,.10),'Sell':(.13,-.35),'Retrofit':(-.7,.13),'Repurpose':(.12,.06),'Redevelop':(-1.45,-.30)}
for a in ar:
    x=px(a['cvar_95_m']);y=py(a['expected_npv_m']);color=BLUE if a['action']=='Sell' else TEAL if a['action']=='Hold' else '8E9CAB'
    circle(s,x-.07,y-.07,.14,color);dx,dy=offset[a['action']];txt(s,x+dx,y+dy,1.42,.32,a['action'],13,color,MED)
rect(s,8.34,2.43,4.48,3.70,PALE,LINE)
sell=next(a for a in ar if a['action']=='Sell');metric(s,8.59,2.68,3.95,f"+S${sell['expected_npv_m']:.2f}m",'Sell: expected gain vs Hold',small=f"S${sell['cvar_95_m']:.2f}m modelled 95% tail loss")
txt(s,8.59,4.94,3.94,.84,'A screening candidate,\nsubject to verified inputs.',20,DARK,LIGHT)
txt(s,8.59,5.88,3.94,.22,'Hold is the relative baseline, not risk-free.',10,GRAY)
takeaway(s,'The plot exposes the trade-off; the evidence gate decides whether it is actionable.')
s.notes_slide.notes_text_frame.text='Data: /portfolio DEMO-001 actions, 5,000 stored scenario observations per action. Loss CVaR95 is the mean worst 5% of max(0, -incremental NPV), using exact tail weights. Zero Hold incremental risk is relative to Hold itself. The independent screening preference is Sell, but all asset-level economics and probabilities are fictional. Plot coordinates are exact values and all graph elements are editable shapes. Raw values are included in decision_data.json.'

# 09 â€” development economics.
s=slide('More floor area does not guarantee more value', 'Monthly development cash flows include full rebuild costs and the existing asset; distinct from annual screening.', '03  /  DEVELOPMENT DECISION',fiction)
cf=adv['redevelopment_cashflow'];txt(s,.55,2.32,7.3,.35,'DEMO-001: monthly investment NPV (S$m)',16,DARK,MED)
vals=[cf['project_npv_m'],cf['hold_npv_m'],cf['npv_m']]
c=chart(s,.48,2.83,7.7,3.30,['Redevelop','Hold','Incremental'],[('NPV',vals)],colors=[BLUE],ymin=-50,ymax=0,major=10,fmt='0.0',labels=True)
for pt,color in zip(c.series[0].points,[BLUE,'A6C8FF',RED]):pt.format.fill.solid();pt.format.fill.fore_color.rgb=rgb(color)
rect(s,8.67,2.48,4.15,3.57,PALE,LINE);metric(s,8.91,2.78,3.69,f"âˆ’S${abs(cf['npv_m']):.2f}m",'Incremental redevelopment NPV',color=RED)
pill(s,8.91,4.71,3.67,'ASSESSED LBC STILL REQUIRED',AMBER,'FFF3DF');txt(s,8.91,5.19,3.69,.78,'The candidate remains\nnot decision-ready.',18,DARK)
takeaway(s,'Use planning capacity to screen an option; use full cash flows to judge the investment.')
s.notes_slide.notes_text_frame.text='Source /assets/DEMO-001/advanced-analysis.redevelopment_cashflow. Expected project NPV -40.154802, Hold investment NPV -3.132386, incremental NPV -37.022416 SGD m. These monthly project cash flows remain separate from the core annual action engine in slide 12; they are not substituted into its rankings or the optimiser. Assessed Land Betterment Charge is missing. Negative redevelopment results already arise before resolving that unknown; this does not establish feasibility or a price for a real site.'

# 10 â€” compare stand-alone rankings and constrained plan.
s=slide('The best portfolio is not the sum of the top asset ideas', 'The income-retention mandate changes which independently attractive sales can be implemented together.', '04  /  PORTFOLIO DECISION',fiction)
txt(s,.57,2.33,7.8,.35,'Illustrative asset counts',16,DARK,MED)
chart(s,.53,2.83,7.42,2.42,['Independent ranks','Constrained plan'],[('Sell',[8,3]),('Hold',[2,7])],XL_CHART_TYPE.BAR_STACKED,[BLUE,'A6C8FF'],True,0,10,2,'0')
rect(s,8.60,2.51,4.22,2.72,PALE,LINE);txt(s,8.85,2.76,3.72,.35,'BASELINE MANDATE',11,BLUE,MED);txt(s,8.85,3.29,3.72,1.62,'Retain at least\n70% of baseline\noperating income.',25,DARK,LIGHT)
for x,val,label in [(.66,'S$167.70m','Sale receipts'),(4.82,'S$9.95m','Expected incremental NPV'),(8.98,'70.1%','Baseline income retained')]:
    txt(s,x,5.60,3.73,.59,val,30,BLUE,LIGHT);txt(s,x,6.31,3.73,.39,label,15,GRAY)
s.notes_slide.notes_text_frame.text='Saved /snapshots/optimise. 8 Sell / 2 Hold are independent core rankings; 3 Sell / 7 Hold is the constrained multi-period solution. Sales: DEMO-001, DEMO-003, DEMO-009. Retained NOI=(25.84-7.73)/25.84=70.0851%. Expected NPV9.947621, receipts167.70, CVaR20.025108, objective3.940089 SGD m at penalty0.3. Sale receipts are capital release, not investment profit.'

# 11 â€” newly computed policy sweep from the same model.
s=slide('Your income mandate changes the capital plan', 'Re-optimise the same fictional portfolio while changing only the minimum retained-income requirement.', '04  /  PORTFOLIO DECISION PLOT', 'Source: six audited model reruns; common inputs and scenario grid. All outcomes are illustrative.')
sweep=DATA['noi_decision_frontier']['points']
px,py=plot_axes(s,1.11,2.88,6.9,2.62,45,105,0,350,[50,60,70,80,90,100],[0,100,200,300],'Minimum baseline income retained (%) â†’','Modelled sale receipts (S$m)')
for a,b in zip(sweep,sweep[1:]):line(s,px(a['minimum_noi_ratio']*100),py(a['capital_released_m']),px(b['minimum_noi_ratio']*100),py(b['capital_released_m']),BLUE,2)
for a in sweep:
    x=px(a['minimum_noi_ratio']*100);y=py(a['capital_released_m']);focus=abs(a['minimum_noi_ratio']-.7)<.001;circle(s,x-.075,y-.075,.15,TEAL if focus else BLUE)
    txt(s,x-.47,y-.47,.95,.30,f"{a['capital_released_m']:.0f}",13,TEAL if focus else BLUE,MED,align=PP_ALIGN.CENTER)
rect(s,8.78,2.48,4.04,3.59,PALE,LINE);txt(s,9.02,2.77,3.55,1.04,'A policy choice,\nmade explicit',25,DARK,LIGHT)
txt(s,9.02,3.86,3.54,1.60,'More income retained\nmeans less capital\navailable from sales\nin this demonstration.',20,GRAY)
takeaway(s,'Agree the mandate first. Then compare feasible plans against it.')
s.notes_slide.notes_text_frame.text='New reproducible sensitivity analysis in analysis/decision_data.json. Total capital500m, liquidity50m, maximum8 concurrent projects, development share0.45, risk penalty0.3, common aligned scenarios. Minimum NOI ratios50%,60%,70%,80%,90%,100%. The saved snapshot uses max_projects20; both limits are nonbinding here. Every displayed plan passed the model constraint audit. These are discrete policy reruns; connecting lines guide the eye and do not imply every intermediate plan is feasible or interpolated.'

# 12 â€” downside not hidden by expected value.
s=slide('A positive expected value can still carry material downside', 'The two-stage model tests a portfolio commitment across three market cases with assumed weights.', '04  /  SCENARIOS AND TRADE-OFFS',fiction)
txt(s,.58,2.33,7.58,.35,'Two-stage portfolio: incremental NPV by case (S$m)',16,DARK,MED)
c=chart(s,.5,2.91,7.60,3.13,['Base\n50% weight','Downside\n25% weight','Upside\n25% weight'],[('NPV',[9.979280,-11.281396,21.857028])],colors=[BLUE],ymin=-15,ymax=30,major=15,fmt='0.0',labels=True)
for pt,col in zip(c.series[0].points,[BLUE,RED,TEAL]):pt.format.fill.solid();pt.format.fill.fore_color.rgb=rgb(col)
rect(s,8.68,2.48,4.14,3.56,PALE,LINE);metric(s,8.93,2.78,3.66,'S$7.63m','Probability-weighted NPV')
txt(s,8.93,4.95,3.65,.94,'Downside case:\nâˆ’S$11.28m',22,RED,LIGHT)
takeaway(s,'Review expected gain and downside together before committing capital.')
s.notes_slide.notes_text_frame.text='Source /snapshots/two-stage. Three assumed cases and weights0.50/0.25/0.25 produce expected incremental NPV7.633548m. The negative downside reflects stressed sale receipts and NPV consistently. These cases are a different scenario set from the core 128-scenario optimisation and should not be presented as a reduction in risk relative to that model. No probability calibration to realised market outcomes is claimed.'

# 13 â€” twins are separate population.
s=slide('Digital twins test how the action mix changes', 'A separate generated underwriting population explores base, stress and structural-change environments.', '04  /  DIGITAL TWIN EXPLORATION', 'Source: /digital-twins/dashboard. Separate synthetic underwriting; values are not comparable with the core portfolio.')
envs=twins['environments'];txt(s,.56,2.33,7.65,.35,'Constrained expected incremental NPV (S$m)',16,DARK,MED)
chart(s,.51,2.86,7.55,3.17,['Base','Stress','Structural change'],[('Expected NPV',[e['portfolio']['portfolio_expected_npv_m'] for e in envs])],colors=[BLUE],ymin=0,ymax=100,major=25,fmt='0.0',labels=True)
rect(s,8.63,2.49,4.20,3.56,PALE,LINE);txt(s,8.89,2.75,3.66,.35,'PORTFOLIO SALES',11,BLUE,MED)
for i,e in enumerate(envs):
    txt(s,8.89,3.37+i*.69,2.57,.36,['Base','Stress','Structural'][i],18,DARK);txt(s,11.63,3.30+i*.69,.63,.49,str(e['portfolio']['allocation']['Sell']),27,BLUE,LIGHT,align=PP_ALIGN.RIGHT)
takeaway(s,'Compare allocations as well as totals: the action mix changes with the environment.')
s.notes_slide.notes_text_frame.text='Twin outputs: constrained NPV79.8007/66.9548/68.0952m; sales6/6/2; receipts420.7940/267.3002/367.5736m. The different action counts reflect asset size and environment-specific income constraints. Synthetic performance does not establish accuracy on real assets. Predictive interval coverage and regret diagnostics are available in the full report; the displayed NPV is model expectation, not realised return.'

# 14 â€” evidence gate, kept visually separate from economic engine.
s=slide('An attractive candidate still needs decision-ready evidence', 'The dashboard separates economic screening from legal, planning and underwriting verification.', '05  /  DECISION GOVERNANCE')
gates=[('Economics','Is the action worth\nmore than Hold?'),('Feasibility','Does it satisfy\nfunding and policy?'),('Evidence','Are critical inputs\nverified and current?')]
for i,(a,b) in enumerate(gates):
    x=.5+i*3.15;rect(s,x,2.70,2.89,2.29,PALE,LINE);txt(s,x+.21,2.95,2.47,.41,a,24,DARK,LIGHT);txt(s,x+.21,3.66,2.47,.95,b,18,GRAY)
    if i<2:line(s,x+2.89,3.83,x+3.13,3.83,BLUE,1.3,True)
line(s,9.69,3.83,10.11,3.83,BLUE,1.3,True)
z=s.shapes.add_shape(MSO_SHAPE.DIAMOND,Inches(10.18),Inches(2.76),Inches(2.54),Inches(2.20));z.fill.solid();z.fill.fore_color.rgb=rgb('FFF3DF');z.line.color.rgb=rgb(GOLD)
txt(s,10.63,3.37,1.64,.88,'Human\nreview',20,AMBER,MED,align=PP_ALIGN.CENTER)
pill(s,.72,5.53,4.88,'PUBLIC DEMO: ALL 10 ASSETS REQUIRE DATA',AMBER,'FFF3DF')
txt(s,6.20,5.41,6.22,.89,'Missing evidence remains visible;\nit is not converted into false certainty.',22,DARK,LIGHT)
s.notes_slide.notes_text_frame.text='Implementation has data readiness/status fields and portfolio constraint audits; all public demo assets are Data Required / Monitor. Assess title, planning, assessed LBC, lease evidence and observed financials before real decisions. Human review is the operating model; public visitors cannot write review signoffs or decision records. Client access control, approvals integration and durable audit storage need a client deployment scope.'

# 15 â€” credible alpha pathway.
s=slide('Turn possible alpha into a testable hypothesis', 'The present evidence supports a working decision system. Investment outperformance still needs validation.', '05  /  VALUE VALIDATION')
for i,(n,title,body) in enumerate([
 ('01','Specify the edge','Identify a repeatable\nleasing, timing or\nrepositioning hypothesis.'),
 ('02','Test out of sample','Use dated inputs and\nan untouched holdout;\ncompare with a baseline.'),
 ('03','Run a client pilot','Measure decision time,\nnet outcomes and\nforecast calibration.')]):
    x=.5+i*4.23;card(s,x,2.45,3.86,3.52,n,title,body)
takeaway(s,'No validated alpha claim today. Agree the benchmark before measuring improvement.')
s.notes_slide.notes_text_frame.text='The revised forecast pipeline separates chronological training, calibration and holdout periods and compares against a naive benchmark. Public forecast cards are formula fixtures, not fitted production model results. Asset-specific alpha hypotheses and decision-policy uplift require verified dated data, transaction costs, unseen outcomes and an agreed counterfactual baseline. These are proposed evaluation steps, not completed client results.'

# 16 â€” architecture without pretending future controls are already deployed.
s=slide('A modular system supports a staged client deployment', 'Separate data, economic calculations and the dashboard so each layer can be reviewed and extended.', '06  /  SYSTEM AND DELIVERY')
columns=[('Data & evidence','Asset inputs\nOfficial market context\nSource provenance'),('Model engines','Valuation & development\nScenarios & optimisation\nReadiness checks'),('Calculation service','Python API\nBounded requests\nVersioned outputs'),('Client workspace','Interactive charts\nDecision comparisons\nWord / PDF reporting')]
for i,(title,body) in enumerate(columns):
    x=.5+i*3.15;rect(s,x,2.54,2.89,2.63,PALE,LINE);txt(s,x+.19,2.78,2.51,.88,title,22,BLUE,LIGHT);txt(s,x+.19,3.99,2.51,1.0,body,15,DARK)
    if i<3:line(s,x+2.89,3.89,x+3.13,3.89,BLUE,1.3,True)
rect(s,.5,5.55,6.03,.92,'F2F4F8');txt(s,.71,5.73,5.61,.54,'Available now\nPublic saved results; local live calculations',14,DARK)
rect(s,6.78,5.55,6.05,.92,'FFF3DF');txt(s,6.98,5.73,5.62,.54,'Deployment step\nConnect Render; scope client security and operations',14,AMBER)
s.notes_slide.notes_text_frame.text='Implemented React/Vite frontend, FastAPI calculation service, Python valuation/scenario/optimisation packages, cached official indices and versioned public snapshots. All 15 public tabs work in GitHub Pages. Docker build and Render blueprint tested; a Render account connection is still required to provision the public backend. The private client production scope must address identity/access, tenancy, durable audit, monitoring and data integration; do not represent these as delivered features.'

# 17 â€” concrete pilot proposal, no fabricated time-saving claim.
s=slide('Start with a pilot that has measurable acceptance criteria', 'Proposed scope: a small, representative asset set and one agreed investment decision mandate.', '06  /  CLIENT PILOT PROPOSAL')
for i,(n,title,body) in enumerate([
 ('GATE 1','Establish the baseline','Validate source data.\nReproduce current\nunderwriting decisions.'),
 ('GATE 2','Review real alternatives','Run agreed scenarios.\nExplain differences and\nresolve material gaps.'),
 ('GATE 3','Measure and decide','Compare with the baseline.\nAccept, refine or stop\nbefore wider rollout.')]):
    card(s,.5+i*4.23,2.45,3.86,3.36,n,title,body)
txt(s,.7,6.15,12,.47,'Measure: review time   â€¢   verified inputs   â€¢   reconciliation   â€¢   decision quality',19,BLUE,MED)
s.notes_slide.notes_text_frame.text='This is a proposed client pilot, not a claimed existing engagement or contractual offer. Agree asset selection, data access, decision mandate, baseline and acceptance thresholds with the client. Model tests already completed:154 backend passed,3 skipped due missing private data;7 frontend passed;TypeScript/build and Linux container passed;all15 public tabs and local calculation controls checked. These are software checks, not evidence of real-world investment outperformance.'

# 18 â€” direct next action and working links.
s=slide('Start with one portfolio and one decision mandate', 'A focused proof of value can show which decisions improve â€” and what evidence is still missing.', '07  /  NEXT DISCUSSION')
for x,n,title,body in [(.58,'01','Choose the assets','A representative sample\nwith accessible records.'),(4.79,'02','Define the mandate','Return, risk, income\nand liquidity priorities.'),(9.0,'03','Agree the benchmark','Current decisions and\nmeasurable acceptance.')]:
    circle(s,x,2.75,.49,BLUE);txt(s,x+.08,2.86,.33,.24,n,12,WHITE,MED,align=PP_ALIGN.CENTER)
    txt(s,x,3.53,3.69,.7,title,25,DARK,LIGHT);txt(s,x,4.42,3.69,.87,body,19,GRAY)
button(s,.6,5.78,4.01,'Explore the public dashboard  â†’',public_url)
button(s,4.94,5.78,3.70,'Read the detailed report  â†’',public_url+'reports/Real_Estate_Dashboard_Interpretation_Report.pdf')
txt(s,9.02,5.83,3.69,.76,'Inspect the assumptions.\nMake the decision.',17,BLUE,MED)
s.notes_slide.notes_text_frame.text='Suggested close: bring the data owner, portfolio manager and investment decision maker into one scoped pilot discussion. Public dashboard and detailed report links are live as of25September2026. The 49-page report has28figures and16tables. The demonstration uses fictional underwriting, official aggregate market context, and does not establish validated alpha.'

assert len(P.slides)==22
for s in P.slides:
    for shape in s.shapes:
        sp=shape._element.find('{http://schemas.openxmlformats.org/presentationml/2006/main}spPr')
        if sp is not None:sp.append(OxmlElement('a:effectLst'))
target=OUT/'Real_Estate_Portfolio_Intelligence_Client_Deck.pptx';P.save(target)
# Set theme fallbacks so charts and newly inserted text retain the reference typography.
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
with ZipFile(target) as z:contents={name:z.read(name) for name in z.namelist()}
for name,raw in list(contents.items()):
    if name.startswith('ppt/charts/chart') and name.endswith('.xml'):
        tree=etree.fromstring(raw)
        for e in tree.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/chart}invertIfNegative'):e.set('val','0')
        for point in tree.findall('.//{http://schemas.openxmlformats.org/drawingml/2006/chart}dPt'):
            tag='{http://schemas.openxmlformats.org/drawingml/2006/chart}invertIfNegative'
            e=point.find(tag)
            if e is None:
                e=etree.Element(tag);point.insert(1,e)
            e.set('val','0')
        contents[name]=etree.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True)
    if name.startswith('ppt/theme/') and name.endswith('.xml'):
        tree=etree.fromstring(raw);ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
        for e in tree.xpath('//a:fontScheme/a:majorFont/a:latin',namespaces=ns):e.set('typeface',LIGHT)
        for e in tree.xpath('//a:fontScheme/a:minorFont/a:latin',namespaces=ns):e.set('typeface',FONT)
        for e in tree.xpath('//a:effectStyle',namespaces=ns):
            for child in list(e):e.remove(child)
            e.append(OxmlElement('a:effectLst'))
        contents[name]=etree.tostring(tree,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(target,'w',ZIP_DEFLATED) as z:
    for name,raw in contents.items():z.writestr(name,raw)
for i,item in enumerate(META):item['notes']=P.slides[i].notes_slide.notes_text_frame.text
(OUT/'slide_manifest.json').write_text(json.dumps({'slides':META,'model_snapshot_sha256':hashlib.sha256(SNAP.read_bytes()).hexdigest(),'reference_pages_used':'1â€“18 only','native_editable':True},indent=2),encoding='utf-8',newline='\n')
print(json.dumps({'pptx':str(target),'slides':len(P.slides),'native_charts':sum(1 for s in P.slides for sh in s.shapes if sh.has_chart),'editable_shapes':sum(len(s.shapes) for s in P.slides)},indent=2))
