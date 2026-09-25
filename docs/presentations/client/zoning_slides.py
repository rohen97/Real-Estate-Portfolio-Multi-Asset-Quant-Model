"""Dedicated zoning outputs and decision-use section for the client deck."""


def add_zoning_section(context):
    globals().update(context)
    s=slide('Zoning produces four different decision inputs',
            'Keep planning controls, ML signals, buildable capacity and investment value distinct.',
            '03  /  ZONING AND ZONING ML',
            'Model trace: zoning lookup, challenger, capacity and advanced valuation modules. Public zoning records are fictional.')
    rows=[
        ('PLANNING CONTEXT','Land use and GPR','Recorded controls,\nspatial match and\nverification flags.','Define the planning\ncase to investigate.'),
        ('ML CHALLENGER','Evidence signals','Predicted class / GPR\nband, uncertainty\nand discrepancies.','Prioritise review\nand monitoring.'),
        ('CAPACITY SCREEN','Area and constraints','Floor-area headroom,\nsetbacks, height\nand envelope options.','Specify candidate\ndevelopment capacity.'),
        ('ECONOMIC TEST','Costed alternatives','Full cash flows,\nresidual land value\nand NPV versus Hold.','Compare development,\nretention and sale.')]
    for i,(kicker,title,body,use) in enumerate(rows):
        x=.5+i*3.15;rect(s,x,2.37,2.89,3.43,PALE,LINE)
        txt(s,x+.18,2.58,2.52,.31,kicker,10.5,BLUE,MED)
        txt(s,x+.18,3.07,2.52,.78,title,22,DARK,LIGHT)
        txt(s,x+.18,3.98,2.52,.94,body,16,GRAY)
        line(s,x+.18,5.02,x+2.71,5.02,LINE,.7)
        txt(s,x+.18,5.20,2.52,.59,use,15,BLUE)
    takeaway(s,'Current integration: ML and detailed development values remain outside the main action rankings.')
    s.notes_slide.notes_text_frame.text=(
        'The four columns are distinct output families, not four additive sources of return. '
        'URA Master Plan describes permissible land use and density; project permission and detailed controls still require verification. '
        'Primary references: https://www.ura.gov.sg/land-planning/master-plan/ and '
        'https://www.ura.gov.sg/guidelines/development-control/. '
        'In the public snapshot legal fields and polygons are fictional fixtures. The ML challenger is a separate diagnostics pathway; '
        'run_asset does not consume the prediction file. The advanced engine passes selected screening-envelope GFA into monthly redevelopment cash flows. '
        'Those detailed cash flows and NPVs are not substituted into the core action templates used by selection and optimisation. '
        'Do not describe ML class disagreement as planning approval or immediately capitalise a screening residual as incremental return.')

    s=slide('Zoning ML challenges the input evidence',
            'Two model targets answer different questions; neither is an automatic Buy, Sell or Hold rule.',
            '03  /  ZONING ML OUTPUTS',
            'Implemented code: LightGBM challenger and zoning-change modules. Public results are hand-authored display fixtures.')
    for x,title,target,outputs,usage in [
        (.5,'Current-zoning challenger','Does the record fit the observed context?',
         'Land-use class / subtype / GPR band\nClass confidence, entropy and abstention\nDiscrepancy status with reasons',
         'Use: investigate mismatches and missing evidence.'),
        (6.79,'Future-change model','Which sites merit closer monitoring?',
         'Zoning / GPR change score\nSeparate from current land-use classification\nRequires dated change labels and validation',
         'Use: a watchlist or an explicit sensitivity case.')]:
        rect(s,x,2.33,6.04,3.43,PALE,LINE)
        txt(s,x+.23,2.57,5.56,.50,title,24,DARK,LIGHT)
        txt(s,x+.23,3.25,5.56,.43,target,17,BLUE)
        txt(s,x+.23,3.99,5.56,1.06,outputs,16,GRAY)
        txt(s,x+.23,5.22,5.56,.38,usage,15,BLUE)
    rect(s,.5,6.06,12.33,.68,'FFF3DF')
    txt(s,.71,6.23,11.91,.47,'Current public demo: no trained predictions. ML scores do not feed action rankings.',17,AMBER)
    s.notes_slide.notes_text_frame.text=(
        'packages/zoning/challenger.py trains separate core, subtype and GPR-band LightGBM classifiers. '
        'Outputs include top-three class probabilities, entropy and abstention, with spatial validation and temperature calibration code. '
        'packages/zoning/change_model.py is a distinct classifier with target changed; its current output has no explicit investment horizon or validated public probability. '
        'A real deployment needs dated change labels, forecast horizon, leakage checks and appropriate holdout evaluation. '
        'Current public /zoning/prediction routes all state synthetic_fixture_not_model; trained=false; abstain=true; future change status=not_estimated. '
        'Any stored illustrative numeric confidence or change value is not a model estimate. '
        'Prediction scripts export diagnostics; their outputs are not consumed by the main cash-flow/action-ranking pipeline or automatically wired into underwriting_readiness. '
        'Operational use today is analyst review of the displayed discrepancy. A forecast-driven valuation connection remains further implementation and validation work.')

    s=slide('Floor-area headroom identifies an option to investigate',
            'DEMO-001: capacity and the separate detailed development model tell different parts of the story.',
            '03  /  ZONING OUTPUT TO ECONOMICS',fiction)
    cap=asset['capacity'];existing=cap['economic_gfa_sqm']-cap['unused_economic_gfa_sqm']
    txt(s,.58,2.32,7.52,.35,'Core capacity screen: gross floor area (sqm)',16,DARK,MED)
    c=chart(s,.49,2.83,7.53,3.17,
            ['Existing\nassumed GFA','GPR-based\nceiling','Adjusted\ncapacity'],
            [('Area',[existing,cap['statutory_gfa_sqm'],cap['economic_gfa_sqm']])],
            colors=[BLUE],ymin=0,ymax=12000,major=4000,fmt='#,##0',labels=True)
    rect(s,8.62,2.42,4.20,3.66,PALE,LINE)
    metric(s,8.87,2.72,3.71,f"{cap['unused_economic_gfa_sqm']:,.0f} sqm",'Unused screened capacity')
    txt(s,8.87,4.94,3.71,.79,'Requires verified controls\nand a costed design.',19,DARK,LIGHT)
    takeaway(s,'Detailed redevelopment test: âˆ’S$37.02m versus Hold, despite the indicated headroom.')
    s.notes_slide.notes_text_frame.text=(
        'Fictional DEMO-001: site2600sqm; assumed GPR4.2; current GFA7862.4sqm; statutory proxy10920sqm; '
        'physical screen10920sqm; de-facto/economic screen10046.4sqm; unused2184sqm. Core screen flags plot ratio and site coverage. '
        'These bars are different quantities, not a waterfall or additive areas. Adjusted capacity is the core heuristic margin/capacity screen, not granted approval. '
        'The separately constructed advanced envelope yields10774.19sqm under different geometry/efficiency assumptions and feeds the monthly development valuation; '
        'it is not the same number as core adjusted capacity. The monthly incremental redevelopment NPV is -37.022416m; assessed LBC is still missing. '
        'This monthly NPV is not fed into the main ranking. The core annual Redevelop template gives a separate -11.374m result. '
        'The S$4.44m simple capacity residual is a diagnostic excluded from additive action returns. '
        'The core annual ranking prefers Sell, but this is driven by assumed cash flows and sale economics, not an ML prediction. '
        'The operational signal remains Data Required / Monitor. Data sources: /portfolio and /assets/DEMO-001/advanced-analysis.')

    s=slide('Translate zoning information into a decision process',
            'Decision-use framework: analyst review is required; the zoning-to-ranking connection is not implemented.',
            '03  /  WHAT DO WE DO WITH THE OUTPUT?',
            'Decision logic guide. Economic candidates remain conditional on verified inputs and portfolio constraints.')
    widths=[3.69,4.45,3.74];xs=[.5,4.39,9.05]
    for x,w,label in zip(xs,widths,['FINDING','WHAT THE TEAM DOES','DECISION IMPLICATION']):
        rect(s,x,2.31,w,.48,PALE);txt(s,x+.15,2.44,w-.30,.22,label,11,BLUE)
    rows=[
        ('ML mismatch or uncertain record','Check the boundary, title and controls.','Review / monitor;\ndefer a final action.'),
        ('Verified capacity and viable costs','Compare improved-use NPV with Hold.','Retrofit, Repurpose or\nRedevelop candidate.'),
        ('Action economics favour retention or exit','Compare Hold with net sale proceeds;\napply risk, income and liquidity limits.','Hold or Sell candidate;\nthen portfolio review.')]
    for i,row in enumerate(rows):
        y=3.04+i*.88
        for x,w,text in zip(xs,widths,row):txt(s,x+.15,y,w-.30,.71,text,16,DARK)
        line(s,.5,y+.77,12.79,y+.77,LINE,.6)
    rect(s,.5,5.98,12.33,.77,'FFF3DF')
    txt(s,.71,6.14,11.91,.51,'Buy is not implemented: acquisition price, transaction costs and a purchase benchmark are required.',17,AMBER)
    s.notes_slide.notes_text_frame.text=(
        'The table explains how a user should use the information, rather than asserting a currently automatic connection from ML into recommendations. '
        'Both the ML diagnostics and detailed zoning-based redevelopment NPVs remain outside the core action-ranking and optimisation path. '
        'The implemented action universe contains Hold, Retrofit, Repurpose, Redevelop and Sell for assets already in the portfolio. '
        'Core ranking maximises expected incremental NPV minus the CVaR penalty; portfolio optimisation enforces shared constraints. '
        'ML output currently supports a separate analyst review; the main engine does not consume its scores. Verified zoning and title are part of underwriting readiness, '
        'but discrepancies are not automatically propagated from the ML prediction file into that gate. '
        'Data Required / Monitor is an evidence status, not an investment recommendation to Hold. '
        'Acquisition signal explicitly states Not assessed: transaction price and benchmark evidence required. '
        'A Buy recommendation would need a separately implemented and tested purchase underwriting comparison. '
        'Zoning forecasts can motivate due diligence and sensitivity cases; they do not justify taking action before evidence and economics have been established.')
