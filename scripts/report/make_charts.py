"""Rebuild report figures from the published dashboard snapshots, without rerunning models."""
from __future__ import annotations
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from matplotlib.ticker import MaxNLocator, PercentFormatter
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
NAVY, TEAL, AMBER, RED, BLUE, GREY = '#16324f', '#168b8b', '#d7a243', '#bb5860', '#578ab7', '#8899a8'
COLORS = {'Hold': GREY, 'Retrofit': TEAL, 'Repurpose': BLUE, 'Redevelop': AMBER, 'Sell': NAVY}
ACTIONS = list(COLORS)
SHORT_ENV = {'base': 'Base', 'stress': 'Stress', 'structural_change': 'Structural'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11.8, 'axes.titlesize': 12.5,
    'axes.labelsize': 11.8, 'xtick.labelsize': 10.5, 'ytick.labelsize': 10.5,
    'legend.fontsize': 10., 'axes.spines.top': False, 'axes.spines.right': False,
    'axes.edgecolor': '#bac7d1', 'axes.labelcolor': NAVY, 'text.color': NAVY,
    'xtick.color': NAVY, 'ytick.color': NAVY, 'axes.grid': True, 'grid.alpha': .18,
    'grid.color': GREY, 'axes.axisbelow': True, 'figure.facecolor': 'white',
    'savefig.facecolor': 'white', 'lines.linewidth': 2., 'axes.prop_cycle': plt.cycler(color=[NAVY, TEAL, AMBER, RED, BLUE])})


def money(value):
    return f'SGD {value:,.2f}m'


def pct(value):
    return f'{value * 100:.1f}%'


def safe(value, default=0.):
    return default if value is None else float(value)


def positive_cvar(values, alpha=.95):
    loss = np.sort(np.maximum(0., -np.asarray(values, float)))[::-1]
    remaining, integral = (1 - alpha) * len(loss), 0.
    for value in loss:
        weight = min(1., remaining)
        integral += weight * value
        remaining -= weight
        if remaining <= 1e-10:
            break
    return integral / ((1 - alpha) * len(loss))


def figure(ncols=1, nrows=1):
    fig, axes = plt.subplots(nrows, ncols, figsize=(10.4, 5.65), squeeze=False)
    fig.subplots_adjust(left=.1, right=.97, bottom=.16, top=.81, wspace=.39, hspace=.38)
    return fig, axes.ravel()


def bars(ax, names, values, color=TEAL, horizontal=False, annotate=True, fmt='.1f'):
    if horizontal:
        names = [textwrap.fill(str(name), 16) for name in names]
        artist = ax.barh(names, values, color=color, height=.65)
        ax.invert_yaxis()
    else:
        artist = ax.bar(names, values, color=color, width=.66)
    if annotate:
        ax.bar_label(artist, labels=[format(v, fmt) for v in values], fontsize=9.8, padding=3)
    ax.margins(y=.2 if not horizontal else .12, x=.17 if horizontal else .08)
    return artist


def interval(ax, actions, low='p10_npv_m', high='p90_npv_m', point='expected_npv_m'):
    names = [a['action'] for a in actions]
    for index, item in enumerate(actions):
        ax.plot([item[low], item[high]], [index, index], color=COLORS[item['action']], lw=5, alpha=.7, solid_capstyle='round')
        ax.scatter(item[point], index, s=48, color=COLORS[item['action']], edgecolors='white', zorder=3)
    ax.set_yticks(range(len(names)), names)
    ax.invert_yaxis()
    ax.axvline(0, color=GREY, lw=1, ls='--')
    ax.set_xlabel('Incremental NPV versus Hold (SGD m)')


def stacked(ax, rows, labels, title=None):
    left = np.zeros(len(rows))
    for action in ACTIONS:
        values = np.array([r.get(action, 0) for r in rows])
        ax.barh(labels, values, left=left, color=COLORS[action], label=action, height=.61)
        for i, value in enumerate(values):
            if value > 0:
                ax.text(left[i] + value / 2, i, f'{value:g}', ha='center', va='center', color='white', fontsize=11, weight='bold')
        left += values
    ax.set_xlim(0, max(left, default=1) * 1.04)
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlabel('Number of assets')
    ax.invert_yaxis()
    if title:
        ax.set_title(title)


class ReportCharts:
    def __init__(self, root=ROOT):
        self.root = root
        self.output = root / 'docs/reports/figures'
        self.output.mkdir(parents=True, exist_ok=True)
        self.api_path = root / 'public/data/api_snapshot.json'
        self.twin_path = root / 'public/data/digital_twin_dashboard.json'
        self.api_bytes = self.api_path.read_bytes()
        self.twin_bytes = self.twin_path.read_bytes()
        self.routes = json.loads(self.api_bytes)['routes']
        self.twins = json.loads(self.twin_bytes)
        self.assets = [value for key, value in self.routes.items()
                       if key.startswith('/assets/') and key.count('/') == 2 and isinstance(value, dict)]
        self.assets.sort(key=lambda a: a['asset_id'])
        self.ids = [a['asset_id'].replace('DEMO-', '') for a in self.assets]
        self.first = self.assets[0]
        self.aid = self.first['asset_id']
        self.advanced = self.routes[f'/assets/{self.aid}/advanced-analysis']
        self.envs = self.twins['environments']
        self.env_labels = [SHORT_ENV[e['id']] for e in self.envs]
        self.manifest = []

    def save(self, fig, identity, title, interpretation, source, units, limitation, section, official=False):
        wrapped_title = textwrap.fill(title, 66)
        two_lines = '\n' in wrapped_title
        if identity != '22_factor_correlation':
            fig.tight_layout(rect=(.025, .105, .975, .81 if two_lines else .86), pad=.65, w_pad=2.1)
        fig.suptitle(wrapped_title, x=.055, ha='left', y=.985, color=NAVY, fontsize=15.5, fontweight='bold')
        banner = 'OFFICIAL MARKET CONTEXT' if official else 'FICTIONAL PORTFOLIO / ILLUSTRATIVE MODEL'
        fig.text(.055, .858 if two_lines else .915, banner, color=TEAL if official else AMBER, fontsize=10, weight='bold')
        fig.text(.075, .03, 'Source: published dashboard snapshot  |  Full interpretation and limitations accompany this figure.', fontsize=8.7, color=GREY)
        filename = f'{identity}.png'
        fig.savefig(self.output / filename, dpi=220)
        plt.close(fig)
        self.manifest.append({'id': identity, 'file': f'figures/{filename}', 'title': title,
            'interpretation': interpretation, 'source': source, 'units': units,
            'limitation': limitation, 'section': section})

    def build(self):
        a, r, t, first = self.assets, self.routes, self.twins, self.first
        ids, envs, env_names = self.ids, self.envs, self.env_labels
        core_value = np.array([x['economics']['current_value_m'] for x in a])
        core_noi = np.array([x['economics']['current_noi_m'] for x in a])
        twin_assets = t['assets']

        fig, ax = figure(2)
        summary = t['portfolio_summary']
        measures = ['Fictional contexts', 'Verified contexts', 'Verified underwriting']
        counts = [summary.get('fictional_asset_contexts', len(a)), summary.get('real_portfolio_anchors', 0),
                  sum(x.get('verified_underwriting_pct', 0) > 0 for x in twin_assets)]
        bars(ax[0], measures, counts, [AMBER, TEAL, NAVY], True, fmt='.0f')
        ax[0].set_xlabel('Assets'); ax[0].set_title('Evidence class')
        complete = np.array([x.get('context_completeness_pct', x.get('real_context_pct', 0)) for x in twin_assets]) * 100
        bars(ax[1], ids, complete, AMBER, annotate=False)
        ax[1].set_ylim(0, 105); ax[1].set_ylabel('Populated context fields (%)'); ax[1].set_xlabel('DEMO asset ID (suffix)')
        self.save(fig, '01_evidence', 'Populated fields do not establish verified evidence',
            f'{counts[0]} asset contexts are fictional and {counts[2]} have verified underwriting. Context completeness averages {np.mean(complete):.1f}%; it measures populated fields, not truth, legal confirmation or financial verification.',
            'digital_twin_dashboard.portfolio_summary and assets; /data/status', 'Asset count; context completeness %',
            'Neither a model output nor a populated coordinate/title field upgrades a fictional input into observed evidence.', 'Evidence and Audit')

        fig, ax = figure(2)
        bars(ax[0], ids, core_value, NAVY, annotate=False); ax[0].set_ylabel('Current proxy value (SGD m)')
        bars(ax[1], ids, core_noi, TEAL, annotate=False); ax[1].set_ylabel('Current proxy annual NOI (SGD m)')
        for axis in ax: axis.set_xlabel('DEMO asset ID (suffix)')
        self.save(fig, '02_portfolio', 'Core portfolio scale and current operating income',
            f'The core proxy portfolio totals {money(core_value.sum())} of current asset value and {money(core_noi.sum())} annual NOI, an aggregate operating yield of {pct(core_noi.sum()/core_value.sum())}. Asset values and recurring income are different quantities; these values do not include incremental action NPVs.',
            '/assets/{id}.economics', 'SGD millions; annual NOI', 'Core proxy and generated twin underwriting use different inputs; their portfolio totals are not interchangeable.', 'Portfolio and Asset')

        opt = r['/snapshots/optimise']
        fig, ax = figure()
        rows = [Counter(x['recommendation']['action'] for x in a), Counter(x['action'] for x in opt['selections'])]
        stacked(ax[0], rows, ['Standalone\ncore screen', 'Constrained\ncore portfolio'])
        ax[0].legend(ncol=5, loc='upper center', bbox_to_anchor=(.5, -.2), frameon=False)
        self.save(fig, '03_core_actions', 'Standalone rankings and portfolio decisions differ',
            f'Standalone recommendations contain {rows[0].get("Sell",0)} Sell and {rows[0].get("Hold",0)} Hold actions. The constrained plan contains {rows[1].get("Sell",0)} Sell and {rows[1].get("Hold",0)} Hold actions. Joint risk, income continuity and funding constrain the final allocation; the sum of independent recommendations is not itself an executable portfolio.',
            '/assets/{id}.recommendation; /snapshots/optimise.selections', 'Asset count',
            'All ten assets remain subject to evidence verification. A preferred action is a provisional research ranking.', 'Portfolio')

        market = r['/market/public']; indicators = market.get('market_indicators', {})
        segments = [s for s in ['private_residential', 'office', 'retail', 'industrial'] if s in indicators]
        seg_labels = ['Private\nresidential' if s == 'private_residential' else s.title() for s in segments]
        fig, ax = figure(2); x = np.arange(len(segments)); width=.33
        facts=[]
        for axis, change in zip(ax, ['qoq', 'yoy']):
            for offset, measure, color in [(-width/2,'price',NAVY),(width/2,'rent',TEAL)]:
                vals = [safe(indicators[s].get(f'{measure}_{change}'), np.nan)*100 for s in segments]
                axis.bar(x+offset, vals, width, label=measure.title(), color=color)
            axis.set_xticks(x, seg_labels); axis.set_ylabel('Index change (%)'); axis.axhline(0,color=GREY,lw=1)
            axis.set_title('Quarter on quarter' if change=='qoq' else 'Year on year'); axis.legend(frameon=False)
        for s in segments:
            val=indicators[s].get('price_qoq')
            if val is not None: facts.append(f'{s.replace("_"," ")} {val*100:+.2f}%')
        self.save(fig, '04_market_changes', 'Official price and rental indices: latest available changes',
            f'Latest price quarter-on-quarter movements are {", ".join(facts)}. Price and rental indices measure sector-level changes, not these assets. The latest snapshot period ends {market.get("as_of")}; office and retail observations cover the Central Region.',
            '/market/public.market_indicators; official URA/JTC datasets via data.gov.sg', 'Percentage change, quarterly and annual',
            'Series can have different latest periods, are potentially revised and do not constitute asset-level forecasts or point-in-time backtests.', 'Official Market Data', True)

        fig, ax = figure(2)
        history = market.get('history', [])
        for axis, measure in zip(ax, ['price', 'rent']):
            for item in history:
                if item['measure'] != measure: continue
                observations=[z for z in item['observations'] if z['period'] >= '2021-Q1']
                if not observations: continue
                origin=observations[0]['index']; years=[int(z['period'][:4])+(int(z['period'][-1])-1)/4 for z in observations]
                axis.plot(years,[z['index']/origin*100 for z in observations], label=item['segment'].replace('private_residential','Residential').title())
            axis.set_title(measure.title()+' index history'); axis.set_ylabel('Rebased index (first shown = 100)'); axis.set_xlabel('Calendar year')
            axis.axhline(100,color=GREY,lw=.8,ls='--'); axis.legend(frameon=False,fontsize=8.7)
        self.save(fig,'05_market_history','Official sector paths rebased for comparison',
            'Each price or rent series is rebased to 100 at its first displayed observation from 2021 onward. A value of 120 means a 20% cumulative increase from that series-specific origin; different index bases have been removed so direction and relative movement can be compared. Divergent sector paths motivate separate underwriting assumptions rather than one market-wide growth rate.',
            '/market/public.history', 'Rebased index; calendar year', 'Rebasing does not make geographic coverage, property mix or publication dates identical. Historical index growth is not a forecast of future asset returns.', 'Official Market Data',True)

        fig, ax = figure(2)
        scores=[x['selection']['risk_adjusted_score_m'] for x in a]
        opportunities=[x['selection']['opportunity']['expected_incremental_npv_m'] for x in a]
        xx=np.arange(len(ids)); ax[0].bar(xx-.17,opportunities,.34,label='Expected incremental NPV',color=TEAL)
        ax[0].bar(xx+.17,scores,.34,label='After risk penalty',color=NAVY); ax[0].set_xticks(xx,ids)
        ax[0].set_ylabel('SGD m versus Hold'); ax[0].legend(frameon=False,fontsize=8.4)
        equivalent=[x['selection']['opportunity']['annual_equivalent_incremental_yield']*100 for x in a]
        bars(ax[1],ids,equivalent,AMBER,annotate=False); ax[1].set_ylabel('Annual-equivalent NPV / value (%)')
        ax[1].set_title('Annuity conversion; not alpha')
        self.save(fig,'06_selection','Selection separates expected value, risk and unsupported alpha',
            f'The displayed standalone expected incremental opportunities sum to {money(sum(opportunities))}; after individual risk penalties the scores sum to {money(sum(scores))}. The annual-equivalent yield converts an NPV into a level annual amount divided by current value. It is not an IRR and must not be added to NOI yield or historical price growth. Independent market alpha remains unestimated.',
            '/assets/{id}.selection', 'SGD m; annual-equivalent proportion of current value', 'Adding asset scores ignores portfolio constraints and joint risk. Break-even additional cost is an NPV allowance, not a construction budget.', 'Selection')

        fig, ax = figure(2)
        sector_counts=Counter(z['segment'] for z in twin_assets); sector_values=Counter()
        for z in twin_assets:sector_values[z['segment']]+=z['valuation_m']
        sectors=list(sector_counts); labels=[textwrap.fill(s,14) for s in sectors]
        bars(ax[0],labels,list(sector_counts.values()),TEAL,True,fmt='.0f'); ax[0].set_xlabel('Assets')
        bars(ax[1],labels,[sector_values[s] for s in sectors],NAVY,True); ax[1].set_xlabel('Generated twin value (SGD m)')
        self.save(fig,'07_twin_sectors','Digital twin sector mix and generated economic scale',
            f'The twin portfolio contains {len(twin_assets)} assets across {len(sectors)} sectors and totals {money(sum(sector_values.values()))}. This is generated twin underwriting. Sector labels preserve office, industrial, mixed-use and hospitality distinctions instead of defaulting unrecognised uses to residential.',
            'digital_twin_dashboard.assets', 'Asset count; generated SGD m', 'Different sector totals reflect both the fixture mix and synthetic generation assumptions; they are not the company portfolio allocation.', 'Digital Twins')

        fig, ax = figure(2)
        stacked(ax[0],[e['recommendation_distribution'] for e in envs],env_names,'Standalone recommendations')
        stacked(ax[1],[e['portfolio'].get('allocation',{}) for e in envs],env_names,'Constrained allocations')
        ax[1].legend(ncol=3,loc='upper center',bbox_to_anchor=(.2,-.19),frameon=False)
        self.save(fig,'08_twin_allocation','Environment recommendations and constrained twin allocations',
            '; '.join(f'{SHORT_ENV[e["id"]]}: {e["recommendation_distribution"].get("Sell",0)} standalone Sell versus {e["portfolio"].get("allocation",{}).get("Sell",0)} constrained Sell' for e in envs)+'. Portfolio income constraints can retain assets even when a standalone sale has the highest expected incremental score.',
            'digital_twin_dashboard.environments', 'Asset count by action and environment', 'Three environments are separate assumption sets, not probability-weighted forecasts; there is no demonstrated real-world optimal policy.', 'Digital Twins')

        fig, ax = figure(2)
        bars(ax[0],env_names,[safe(e['portfolio'].get('portfolio_expected_npv_m')) for e in envs],TEAL)
        ax[0].set_ylabel('Expected incremental NPV (SGD m)')
        x=np.arange(len(envs));width=.34
        ax[1].bar(x-width/2,[e['portfolio'].get('capital_required_m',0) for e in envs],width,label='Gross capex',color=AMBER)
        ax[1].bar(x+width/2,[e['portfolio'].get('capital_released_m',0) for e in envs],width,label='Sale receipts',color=NAVY)
        ax[1].set_xticks(x,env_names); ax[1].set_ylabel('Undiscounted funding (SGD m)');ax[1].legend(frameon=False)
        self.save(fig,'09_twin_value_funding','Economic value and cash released are different quantities',
            '; '.join(f'{SHORT_ENV[e["id"]]}: expected incremental NPV {money(safe(e["portfolio"].get("portfolio_expected_npv_m")))}, sale receipts {money(safe(e["portfolio"].get("capital_released_m")))}' for e in envs)+'. Sale proceeds are large because ownership is transferred; NPV deducts the forgone Hold income and residual value. Releasing cash does not imply creating the same amount of profit.',
            'digital_twin_dashboard.environments[].portfolio', 'SGD m: present value versus undiscounted cash', 'These remain two distinct accounting bases. A zero development allocation is a valid output under costly redevelopment assumptions.', 'Digital Twins')

        twin=twin_assets[0]; twin_actions=twin['environments']['base']['actions']
        fig, ax=figure();interval(ax[0],twin_actions)
        chosen=twin['environments']['base']
        self.save(fig,'10_twin_intervals',f'Twin action uncertainty: {twin["asset_id"]}, base environment',
            f'The selected twin action is {chosen["recommended_action"]}, with expected incremental NPV {money(chosen["expected_npv_m"])} and P10–P90 range {money(chosen["p10_m"])} to {money(chosen["p90_m"])}. Lines show the central 80% of simulated outcomes and dots the sample mean. Hold stays at exactly zero because every alternative is measured against the same Hold cashflows.',
            f'digital_twin_dashboard.assets[{twin["asset_id"]}].environments.base.actions', 'Incremental NPV, SGD m', 'Intervals combine uncalibrated action assumptions, approval branches and simulated shocks; they are not investment-grade confidence intervals.', 'Digital Twins')

        fig, ax=figure(2)
        coverage=[e['p10_p90_coverage']*100 for e in envs];agreement=[e['correct_action_rate_vs_simulation']*100 for e in envs]
        bars(ax[0],env_names,coverage,TEAL);ax[0].axhline(80,color=AMBER,ls='--',label='Nominal interval: 80%');ax[0].set_ylim(0,110);ax[0].set_ylabel('Held-out simulated outcomes covered (%)');ax[0].legend(frameon=False,fontsize=9)
        bars(ax[1],env_names,agreement,NAVY);ax[1].set_ylim(0,110);ax[1].set_ylabel('Agreement with simulated hindsight action (%)')
        self.save(fig,'11_twin_diagnostics','Simulation coverage and hindsight agreement test different things',
            '; '.join(f'{n}: interval coverage {c:.0f}% and simulated action agreement {h:.0f}%' for n,c,h in zip(env_names,coverage,agreement))+'. Coverage tests whether generated outcomes lie within their central intervals; agreement tests whether the recommended action matches a hindsight choice. They use different denominators and cannot be compared as one accuracy metric.',
            'digital_twin_dashboard.environments[].p10_p90_coverage and correct_action_rate_vs_simulation', 'Percent; nominal coverage 80%', 'The evaluation uses a separate synthetic draw and latent outcome adjustment, not observed market outcomes. Ten assets make action percentages coarse.', 'Digital Twins')

        fig, ax=figure(2)
        matrix=np.array([[z['environments'][e['id']]['decision_regret_m'] for e in envs] for z in twin_assets])
        im=ax[0].imshow(matrix,aspect='auto',cmap='YlOrBr');ax[0].set_xticks(range(len(envs)),env_names);ax[0].set_yticks(range(len(ids)),ids);ax[0].set_ylabel('DEMO asset ID');ax[0].grid(False);fig.colorbar(im,ax=ax[0],label='Hindsight regret (SGD m)',fraction=.05,pad=.04)
        bars(ax[1],ids,[z['stability_score']*100 for z in twin_assets],TEAL,annotate=False);ax[1].set_ylim(0,110);ax[1].set_ylabel('Modal recommendation frequency (%)')
        self.save(fig,'12_twin_regret','Regret measures missed simulated opportunity; stability measures consistency',
            f'There are {sum(bool(z["fragile"]) for z in twin_assets)} assets whose recommendations change across the three environments. The largest single asset/environment hindsight regret is {money(float(matrix.max()))}. A stable action can still have regret, because consistency does not imply that the model foresaw the highest simulated outcome.',
            'digital_twin_dashboard.assets[].environments and stability_score', 'SGD m regret; modal frequency %', 'Twin stability uses three environments and a change-based fragility flag. It differs from the optimiser perturbation stability test.', 'Digital Twins')

        fig, ax=figure();x=np.arange(len(a));width=.19
        fields=[('statutory_gfa_sqm','Statutory',GREY),('physical_gfa_sqm','Physical',NAVY),('expected_approved_gfa_sqm','Expected approved',TEAL),('economic_gfa_sqm','Economic screen',AMBER)]
        for k,(field,label,color) in enumerate(fields):ax[0].bar(x+(k-1.5)*width,[z['capacity'][field]/1000 for z in a],width,label=label,color=color)
        ax[0].set_xticks(x,ids);ax[0].set_ylabel('Gross floor area (thousand sqm)');ax[0].set_xlabel('DEMO asset ID (suffix)');ax[0].legend(ncol=2,frameon=False,fontsize=9.7)
        self.save(fig,'13_capacity','Planning capacity is a sequence of distinct screening quantities',
            f'For {self.aid}, statutory GFA is {first["capacity"]["statutory_gfa_sqm"]:,.0f} sqm, physical GFA {first["capacity"]["physical_gfa_sqm"]:,.0f} sqm and expected approved GFA {first["capacity"]["expected_approved_gfa_sqm"]:,.0f} sqm. The economic screen can exceed probability-weighted approved area because those quantities answer different questions; they must not be added together.',
            '/assets/{id}.capacity', 'Thousand square metres GFA', 'GPR labels, parcel boundaries, physical limits and approval probabilities are unverified fixture/proxy inputs; no legal development entitlement is established.', 'Zoning')

        fig, ax=figure(2);bindings=Counter(v for z in a for v in z['capacity'].get('binding_constraints',[]))
        bars(ax[0],[v.replace('_',' ').title() for v in bindings],list(bindings.values()),TEAL,True,fmt='.0f');ax[0].set_xlabel('Assets with each binding screen')
        zoning=[r[f'/zoning/prediction/{z["asset_id"]}'] for z in a]
        matched=sum(z['discrepancy']['legal_core']==z['discrepancy']['predicted_core'] for z in zoning)
        bars(ax[1],['Fixture label\nagreement','Verified legal\nmatches','Trained zoning\nmodels'],[matched,0,sum(bool(z['prediction'].get('trained')) for z in zoning)], [AMBER,GREY,NAVY],fmt='.0f')
        ax[1].set_ylabel('Count');ax[1].set_ylim(0,len(a)+2)
        self.save(fig,'14_zoning_diagnostics','Binding constraints and zoning display fixtures',
            f'The most frequent binding screen is {bindings.most_common(1)[0][0].replace("_"," ")} ({bindings.most_common(1)[0][1]} assets). {matched}/{len(zoning)} fixture labels match their supplied legal-style labels, but no zoning model was trained and these are not independently verified legal matches. Agreement is chart plumbing, not measured classification accuracy.',
            '/assets/{id}.capacity; /zoning/prediction/{id}', 'Asset count; fixture label count', 'The displayed confidence and future-change numbers are hand-authored, uncalibrated fixtures; abstention and evidence review remain required.', 'Zoning ML')

        fig,ax=figure(2);adv=self.advanced;site=adv['site_polygon'];coords=np.array(site['coordinates'][0]);center=coords.mean(axis=0);scale=np.array([111320*np.cos(np.radians(center[1])),110540]);local=(coords-center)*scale
        ax[0].add_patch(Polygon(local,facecolor='#e8eef2',edgecolor=NAVY,label='Synthetic parcel'))
        envelope=adv['development_envelope'];preferred=envelope.get('preferred') or {}
        for geometry in preferred.get('footprints_geojson',[]):
            rings=geometry['coordinates'] if geometry['type']=='Polygon' else geometry['coordinates'][0]
            ax[0].add_patch(Polygon((np.array(rings[0])-center)*scale,facecolor=TEAL,alpha=.65,edgecolor=TEAL))
        ax[0].autoscale_view();ax[0].set_aspect('equal');ax[0].set_xlabel('Approx. local east (m)');ax[0].set_ylabel('Approx. local north (m)');ax[0].set_title('Site and preferred floorplates')
        options=envelope.get('options',[]);names=[f'{o["towers"]} tower(s)\n{o["storeys"]} storeys' for o in options]
        bars(ax[1],names,[o['gross_gfa_sqm']/1000 for o in options],TEAL);ax[1].set_ylabel('Screened gross floor area (thousand sqm)')
        self.save(fig,'15_envelope',f'Development envelope screening: {self.aid}',
            f'The preferred envelope has {preferred.get("towers",0)} tower(s), {preferred.get("storeys",0)} storeys and {preferred.get("gross_gfa_sqm",0):,.0f} sqm GFA. The site is a synthetic rectangle and the footprint is a geometric screen constrained by GPR, height, coverage and setbacks. Surrounding-building evidence is {adv["viewshed"].get("status","unavailable")}; missing geometry does not establish an open view.',
            f'/assets/{self.aid}/advanced-analysis.site_polygon and development_envelope', 'Approximate local metres; thousand sqm', 'Not a surveyed cadastral plot, architect design, parking/fire approval or verified viewshed. If no feasible envelope exists, no redevelopment value is reported.', 'Development')

        cash=adv['redevelopment_cashflow'];flows=np.array(cash.get('monthly_cashflows_m',[]),float)
        fig,ax=figure(2)
        if flows.size:
            months=np.arange(len(flows));ax[0].bar(months,flows,color=np.where(flows>=0,TEAL,RED),width=.95)
            ax[1].plot(months,np.cumsum(flows),color=NAVY)
            for axis in ax:axis.axhline(0,color=GREY,lw=1);axis.set_xlabel('Month from decision')
            ax[0].set_ylabel('Expected incremental cashflow (SGD m)');ax[1].set_ylabel('Cumulative undiscounted cashflow (SGD m)')
        else:
            for axis in ax:axis.text(.5,.5,'No feasible envelope;\nno cashflow valuation',ha='center',va='center',transform=axis.transAxes)
        self.save(fig,'16_monthly_cashflow',f'Monthly redevelopment economics versus Hold: {self.aid}',
            f'The expected unlevered incremental NPV is {money(safe(cash.get("npv_m")))} over {cash.get("months",0)} months, before any unassessed LBC. Negative bars represent extra costs or forgone Hold income; the final month includes the difference in disposal proceeds. The cumulative line is undiscounted cash and therefore does not equal NPV. Project and Hold both include the same current-asset opportunity cost at time zero.',
            f'/assets/{self.aid}/advanced-analysis.redevelopment_cashflow', 'SGD m; month', 'LBC is missing and underwriting is unverified. These displayed calculations are not decision-ready and are not levered equity cashflows.', 'Development')

        fig,ax=figure(2);cost_keys=[('construction_m','Build'),('professional_fees_m','Fees'),('contingency_m','Contingency'),('demolition_m','Demolition'),('tenant_relocation_m','Relocation')]
        bars(ax[0],[label for key,label in cost_keys],[safe(cash.get(key)) for key,label in cost_keys],TEAL,annotate=False);ax[0].set_ylabel('Known project cost (SGD m)');ax[0].tick_params(axis='x',rotation=25)
        debt=np.array(cash.get('monthly_closing_debt_m',[]),float);draws=np.array(cash.get('monthly_debt_draws_m',[]),float)
        if len(debt):
            ax[1].plot(np.arange(len(debt)),np.cumsum(draws),label='Cumulative loan draws',color=GREY,ls='--');ax[1].plot(np.arange(len(debt)),debt,label='Closing loan balance',color=NAVY)
        ax[1].set_xlabel('Month');ax[1].set_ylabel('Success-conditional borrowing (SGD m)');ax[1].legend(frameon=False,fontsize=9)
        self.save(fig,'17_cost_debt','Full rebuilding cost and reconciled development debt',
            f'{self.aid} incurs {money(safe(cash.get("construction_m")))} construction cost on all {cash.get("construction_gfa_sqm",0):,.0f} rebuilt sqm. Conditional debt draws total {money(safe(cash.get("total_debt_draws_m")))}, equal to principal repayment {money(safe(cash.get("debt_repayment_m")))}; interest totals {money(safe(cash.get("financing_interest_m")))}. Equity receives the loan draws before paying interest and repayment, while unlevered decision NPV excludes financing.',
            f'/assets/{self.aid}/advanced-analysis.redevelopment_cashflow', 'SGD m; months; full rebuilt sqm', 'Debt series are conditional on successful development, not probability-weighted net borrowing. LBC is an unknown omitted charge, not zero.', 'Development')

        fig,ax=figure(2);eb=adv['enbloc'];keys=['construction_m','professional_m','finance_m','marketing_m','developer_margin_m','demolition_m','tenant_cost_m','buyer_stamp_duty_m']
        known=sum(safe(eb.get(k)) for k in keys);labels=['Gross\ndevelopment\nvalue','Known costs\nand required\nmargin','Residual\nland offer'];vals=[eb['gross_development_value_m'],known,eb['maximum_land_value_m']]
        bars(ax[0],labels,vals,[NAVY,AMBER,TEAL]);ax[0].set_ylabel('SGD m');ax[0].text(.03,.94,'LBC unassessed / excluded',transform=ax[0].transAxes,color=RED,fontsize=10,weight='bold')
        all_eb=[r[f'/assets/{z["asset_id"]}/advanced-analysis']['enbloc'] for z in a]
        x=np.arange(len(a));ax[1].bar(x-.17,core_value,.34,color=GREY,label='Current proxy value');ax[1].bar(x+.17,[e['maximum_land_value_m'] for e in all_eb],.34,color=TEAL,label='Residual land offer')
        ax[1].set_xticks(x,ids);ax[1].set_ylabel('SGD m');ax[1].legend(frameon=False,fontsize=9)
        self.save(fig,'18_enbloc','En-bloc residual value reconciles known costs, not unknown charges',
            f'For {self.aid}, gross development value {money(eb["gross_development_value_m"])} less known costs and developer margin {money(known)} leaves a land offer of {money(eb["maximum_land_value_m"])}. Buyer duty is solved on that offer. The offer is below the current proxy value of {money(core_value[0])}; the chart does not infer that owners would accept it. Failure retains the asset, which is included in the separate incremental comparison.',
            '/assets/{id}/advanced-analysis.enbloc', 'SGD m, undiscounted development residual', 'LBC and acquisition-finance/tenure-top-up evidence are incomplete; the residual is an incomplete screening amount. Consent probabilities remain uncalibrated.', 'Development')

        fig,ax=figure(2);dcf=first['dcf'];econ=first['economics'];flows=np.array(dcf['cashflows_m']);terminal=dcf['terminal_value_m'];noi=flows.copy();noi[-1]-=terminal;years=np.arange(1,len(noi)+1)
        bars(ax[0],years,noi,TEAL,annotate=False);ax[0].set_xlabel('End of year');ax[0].set_ylabel('NOI before terminal sale (SGD m)')
        tpv=terminal/(1+econ['discount_rate'])**len(noi);income_pv=dcf['value_m']-tpv
        bars(ax[1],['Income\nPV','Terminal\nPV'],[income_pv,tpv],[TEAL,NAVY]);ax[1].set_ylabel('Present value (SGD m)')
        self.save(fig,'19_dcf',f'Core Hold DCF: operating income and terminal value separated',
            f'{self.aid} has a Hold DCF of {money(dcf["value_m"])}: {money(income_pv)} from operating income and {money(tpv)} from discounted net terminal value. Terminal PV is {pct(tpv/dcf["value_m"])} of total value. That concentration explains sensitivity to exit cap rate and terminal NOI. The {money(terminal)} terminal cash receipt is not recurring annual NOI.',
            f'/assets/{self.aid}.dcf and economics', 'SGD m; year-end periods', 'NOI growth, cap rate and asset costs remain proxy assumptions; sensitivity to terminal value is a valuation dependency, not evidence of overvaluation.', 'Valuation')

        core_actions=first['actions'];fig,ax=figure(2);interval(ax[0],core_actions)
        bars(ax[1],[z['action'] for z in core_actions],[z['probability_of_loss']*100 for z in core_actions],[COLORS[z['action']] for z in core_actions],True)
        ax[1].set_xlim(0,110);ax[1].set_xlabel('Probability of negative incremental NPV (%)')
        self.save(fig,'20_core_action_risk',f'Core action ranges and loss probability: {self.aid}',
            f'The core screen selects {first["recommendation"]["action"]}. A P10 below zero indicates lower-tail incremental losses, while the probability panel reports the fraction of all simulated outcomes below zero. Hold has zero incremental risk by construction. P10 is a quantile, not the probability of a 10% loss.',
            f'/assets/{self.aid}.actions', 'Incremental NPV SGD m; probability %', 'These core scenarios use size-scaled factor exposures and approval branches. They differ from the twin environment engine and must not be merged into one distribution.', 'Actions')

        fig,ax=figure(3);stored=r[f'/assets/{self.aid}/scenario-samples'];sample_stats=[]
        for axis,name in zip(ax,['Retrofit','Redevelop','Sell']):
            values=np.array(stored['samples'][name]);axis.hist(values,bins=45,color=COLORS[name],alpha=.82,density=True);axis.axvline(0,color=RED,lw=1,ls='--');axis.axvline(values.mean(),color=NAVY,lw=1.5);axis.set_title(name);axis.set_xlabel('Incremental NPV (SGD m)')
            sample_stats.append(f'{name}: mean {values.mean():.2f}m, loss frequency {np.mean(values<0)*100:.1f}%')
        ax[0].set_ylabel('Probability density');fig.subplots_adjust(wspace=.32)
        self.save(fig,'21_distributions',f'Stored core simulation draws: {self.aid}',
            f'Histograms use the same {stored["draws"]:,} stored model draws as the reported core metrics; they are not regenerated chart samples. '+ '; '.join(sample_stats)+'. The dashed red line is zero incremental NPV, and the solid line marks the sample mean. Multiple modes can reflect success and failed-execution branches.',
            f'/assets/{self.aid}/scenario-samples', 'SGD m; probability density integrates to one', 'A smooth-looking distribution does not validate its assumed exposures, calibration or tail probabilities. Density heights are not probabilities at individual values.', 'Scenario')

        fig,ax=figure(2);cov=r['/visualisations/scenario-matrix'];labels=['Rent','Vacancy','Cap rate','Interest','Cost','Delay']
        for axis,key,title in zip(ax,['input_correlation','correlation'],['Input dependence','Realised bounded draws']):
            matrix=np.array(cov[key]);image=axis.imshow(matrix,vmin=-1,vmax=1,cmap='BrBG');axis.grid(False);axis.set_title(title);axis.set_xticks(range(6),labels,rotation=40,ha='right');axis.set_yticks(range(6),labels)
            for i in range(6):
                for j in range(6):axis.text(j,i,f'{matrix[i,j]:.2f}',ha='center',va='center',fontsize=8,color='white' if abs(matrix[i,j])>.7 else NAVY)
        fig.subplots_adjust(left=.11,right=.96,bottom=.3,top=.79,wspace=.4)
        color_axis=fig.add_axes([.3,.13,.43,.026])
        fig.colorbar(image,cax=color_axis,orientation='horizontal',label='Correlation')
        self.save(fig,'22_factor_correlation','Input correlation and realised scenario dependence',
            f'The scenario source is {cov["status"].replace("_"," ")}. The realised rent-growth/cap-rate correlation is {cov["correlation"][0][2]:.2f}; a negative value links stronger rent with lower cap rates in this simulation. Clipping and tail mixing can change realised correlations from the input matrix, so both are shown.',
            '/visualisations/scenario-matrix', 'Pearson correlation, -1 to +1', 'Fallback correlations are modelling assumptions, not measured market relationships; even a calibrated factor matrix does not validate action-level sensitivities.', 'Scenario')

        fig,ax=figure(2);plan=opt['annual_plan'];years=[p['year'] for p in plan]
        ax[0].bar(years,[p['capex_m'] for p in plan],color=AMBER,label='Capex');ax[0].bar(years,[-p['capital_released_m'] for p in plan],color=TEAL,label='Sale receipts (offset)');ax[0].plot(years,opt['constraints']['annual_capital_budgets'],color=NAVY,ls='--',label='Annual net funding limit');ax[0].set_ylabel('Undiscounted funding (SGD m)');ax[0].set_xlabel('Decision year');ax[0].legend(frameon=False,fontsize=8.7)
        retained=[core_noi.sum()-p['noi_disruption_m'] for p in plan];ax[1].plot(years,retained,marker='o',color=TEAL,label='Retained baseline NOI');threshold=core_noi.sum()*opt['constraints']['minimum_noi_ratio'];ax[1].axhline(threshold,color=AMBER,ls='--',label='Minimum income constraint');ax[1].set_ylabel('Baseline annual NOI (SGD m)');ax[1].set_xlabel('Decision year');ax[1].set_ylim(0,core_noi.sum()*1.08);ax[1].legend(frameon=False,fontsize=9)
        self.save(fig,'23_optimiser_funding','Capital scheduling and retained income in the core allocation',
            f'The selected plan spends {money(sum(p["capex_m"] for p in plan))} and releases {money(sum(p["capital_released_m"] for p in plan))}. Lowest retained baseline NOI is {money(min(retained))}, versus the {money(threshold)} minimum. Sale cash offsets funding only at its scheduled settlement; sold assets stop contributing baseline income. The independent constraint audit reports {opt["constraint_violations"]} violations.',
            '/snapshots/optimise.annual_plan and constraints', 'SGD m; decision year', 'Income continuity is a baseline loss screen, not a full future operating statement; budgeted liquidity is not a bank-account forecast.', 'Optimiser')

        fig,ax=figure(2);aligned=[]
        for selection in opt['selections']:
            asset=next(z for z in a if z['asset_id']==selection['asset_id']);action=next(z for z in asset['actions'] if z['action']==selection['action'])
            if action.get('scenario_npvs_m'):
                aligned.append(np.array(action['scenario_npvs_m'])*selection.get('discount_factor',1))
        joint=safe(opt.get('portfolio_loss_cvar_m'));marginal=sum(positive_cvar(v) for v in aligned) if aligned else safe(opt.get('sum_of_marginal_cvar_95_m'))
        bars(ax[0],['Portfolio\njoint loss CVaR','Sum of marginal\nCVaR, same draws'],[joint,marginal],[TEAL,AMBER]);ax[0].set_ylabel('95% loss CVaR (SGD m)')
        bars(ax[1],['Expected\nincremental NPV','After joint\nrisk penalty'],[opt['portfolio_expected_npv_m'],opt['risk_adjusted_objective_m']],[TEAL,NAVY]);ax[1].set_ylabel('Portfolio value (SGD m)')
        self.save(fig,'24_joint_risk','Joint portfolio risk must use aligned scenario outcomes',
            f'The core allocation has expected incremental NPV {money(opt["portfolio_expected_npv_m"])} and joint positive-part-loss CVaR {money(joint)}. On the same scenario grid, the sum of selected marginal CVaRs is {money(marginal)}. Correlations and offsetting outcomes determine the difference. The risk-adjusted objective is {money(opt["risk_adjusted_objective_m"])} after the configured penalty.',
            '/snapshots/optimise plus selected /assets/{id}.actions.scenario_npvs_m', 'SGD m; 95% CVaR of positive-part loss', 'Compare joint and marginal CVaR on the same draw grid. The optimiser uses a reduced scenario grid and does not prove empirical diversification or safe tails.', 'Optimiser')

        two=r['/snapshots/two-stage'];recourse=two['recourse'];fig,ax=figure(2)
        bars(ax[0],[z['scenario'] for z in recourse],[z['portfolio_npv_m'] for z in recourse],TEAL);ax[0].axhline(0,color=GREY,lw=1);ax[0].set_ylabel('Scenario portfolio incremental NPV (SGD m)')
        allocations=[Counter(z['action'] for z in s['selections']) for s in recourse];stacked(ax[1],allocations,[s['scenario'] for s in recourse]);ax[1].legend(ncol=3,loc='upper center',bbox_to_anchor=(.5,-.19),frameon=False,fontsize=8.4)
        self.save(fig,'25_two_stage','Two-stage scenarios connect commitments with funded recourse',
            f'Probability-weighted portfolio incremental NPV is {money(two["portfolio_expected_npv_m"])} and positive-part-loss CVaR is {money(two["portfolio_loss_cvar_m"])}. '+ '; '.join(f'{z["scenario"]}: {money(z["portfolio_npv_m"])} with {len(z["cancelled"])} cancellations' for z in recourse)+'. Cancelling retains Hold economics and pays a decision-year fee; delayed projects must still finish inside the horizon.',
            '/snapshots/two-stage', 'SGD m by scenario; executed/fallback asset counts', 'Scenario probabilities and multipliers are assumptions. This is not a continuously rebalanced policy or a calibrated multi-year macro forecast.', 'Optimiser')

        stable=r['/snapshots/stability'];fig,ax=figure();rows=stable['assets'];x=np.arange(len(rows))
        ax[0].bar(x-.18,[safe(z['stability_score'])*100 for z in rows],.36,color=TEAL,label='Most frequent action')
        ax[0].bar(x+.18,[safe(z.get('baseline_action_frequency'))*100 for z in rows],.36,color=NAVY,label='Original action frequency')
        ax[0].axhline(70,color=AMBER,ls='--',label='Fragility threshold: 70%');ax[0].set_xticks(x,[z['asset_id'].replace('DEMO-','') for z in rows]);ax[0].set_ylim(0,112);ax[0].set_ylabel('Frequency in feasible perturbation runs (%)');ax[0].set_xlabel('DEMO asset ID (suffix)');ax[0].legend(frameon=False,fontsize=9.8)
        self.save(fig,'26_stability','Optimiser stability is sensitivity, not prediction accuracy',
            f'{stable["successful_runs"]}/{stable["runs"]} perturbation runs were feasible; {stable["fragile_assets"]} assets have a modal action frequency below 70%. The most frequent action can differ from the original allocation. The arithmetic mean expected NPV across these perturbation solutions is {money(stable["portfolio_expected_npv_mean_m"])}; it is not an out-of-sample return.',
            '/snapshots/stability', 'Action frequency %; feasible-run denominator', 'Asset-by-asset modal actions need not form one jointly feasible portfolio. Perturbation stability and three-environment twin stability have different denominators.', 'Optimiser')

        back=r['/models/backtest'];pred=back['predictions'];actual=np.array([z['actual_noi_m'] for z in pred]);point=np.array([z['point'] for z in pred]);fig,ax=figure(3)
        low,high=min(actual.min(),point.min())*.96,max(actual.max(),point.max())*1.04
        ax[0].plot([low,high],[low,high],color=GREY,ls='--');ax[0].scatter(actual,point,color=TEAL,s=35);ax[0].set_xlabel('Fictional target NOI (SGD m)');ax[0].set_ylabel('Formula point NOI (SGD m)')
        bars(ax[1],[z['asset_id'].replace('DEMO-','') for z in pred],(point-actual)*1000,RED,annotate=False);ax[1].set_ylabel('Point minus target (SGD thousands)');ax[1].set_xlabel('DEMO asset ID');ax[1].tick_params(axis='x',rotation=45)
        coverage=np.mean([(z['p10']<=z['actual_noi_m']<=z['p90']) for z in pred]);bars(ax[2],['Measured\nfixture','Nominal\ninterval'],[coverage*100,80],[TEAL,AMBER],fmt='.0f');ax[2].set_ylim(0,115);ax[2].set_ylabel('Coverage (%)')
        self.save(fig,'27_forecast_examples','Forecast display examples reconcile; they are not a trained-model backtest',
            f'Recomputing the {len(pred)} fictional formula rows gives MAE SGD {float(np.mean(abs(point-actual)))*1e6:,.0f}, mean bias SGD {float(np.mean(point-actual))*1e6:,.0f} and interval coverage {pct(coverage)}. The tight scatter is a consequence of the example formula, not evidence of forecasting skill. No learned production artifact or independent historical investment outcome is used by these cards.',
            '/models/backtest.predictions and noi_forecast', 'SGD m; residual SGD thousands; coverage %', 'The strengthened forecasting pipeline supports chronological train/calibration/holdout evaluation separately; these public fixture cards do not show a fitted model evaluation.', 'Models')

        fig,ax=figure();axis=ax[0];axis.axis('off')
        boxes=[(.02,.58,.22,.23,'INPUT EVIDENCE','Fictional assets\nOfficial sector context'),(.32,.58,.26,.23,'ECONOMIC ENGINES','Core DCF / monthly projects\nTwin environment scenarios'),(.67,.58,.29,.23,'DECISION SCREENS','Hold-relative NPV and risk\nConstrained capital plans'),(.02,.12,.26,.23,'VERIFICATION GATES','Titles / leases / costs / LBC\nProvenance and audit'),(.38,.12,.26,.23,'PUBLIC SNAPSHOT','Saved results and charts\nBrowser filtering only'),(.74,.12,.22,.23,'LIVE API OPTION','Hosted Python backend\nNew calculations')]
        for x,y,w,h,heading,body in boxes:
            axis.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.012,rounding_size=.02',facecolor='#eef4f6',edgecolor=TEAL,transform=axis.transAxes))
            axis.text(x+w/2,y+h*.73,heading,ha='center',va='center',weight='bold',fontsize=9.8,transform=axis.transAxes)
            axis.text(x+w/2,y+h*.34,body,ha='center',va='center',fontsize=9.1,transform=axis.transAxes)
        for start,end in [((.245,.69),(.305,.69)),((.59,.69),(.655,.69)),((.81,.56),(.52,.37)),((.155,.37),(.42,.56))]:axis.annotate('',xy=end,xytext=start,arrowprops={'arrowstyle':'->','lw':1.8,'color':NAVY},xycoords='axes fraction')
        axis.text(.5,-.02,'Separate modelling assumptions remain visible; shared accounting identities and provenance connect them.',ha='center',fontsize=9.5,transform=axis.transAxes)
        self.save(fig,'28_architecture','Model pathways, evidence gates and publication boundaries',
            'Official sector indices enrich context; they do not replace missing asset underwriting. Core valuation, detailed projects and digital twins retain distinct assumptions and units. Scenario outcomes feed constrained optimisation, while evidence gates determine whether a recommendation can be used. The public snapshot serves saved results; a connected Python backend is required for new calculations.',
            'Repository architecture; API snapshot metadata; model provenance', 'Workflow diagram; no quantitative scale', 'This diagram describes implemented capabilities and dependencies, not confirmation that a cloud backend is deployed, calibrated or using private company data.', 'Architecture and Audit')

        payload={'schema_version':1,'chart_count':len(self.manifest),'sources':{
            'api_snapshot_sha256':sha256(self.api_bytes).hexdigest(),
            'digital_twin_dashboard_sha256':sha256(self.twin_bytes).hexdigest()},'figures':self.manifest}
        (self.root/'docs/reports/chart_manifest.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False),encoding='utf-8',newline='\n')
        return payload


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args()
    result=ReportCharts(args.root).build();print(json.dumps({'chart_count':result['chart_count'],'manifest':str(args.root/'docs/reports/chart_manifest.json')}))
