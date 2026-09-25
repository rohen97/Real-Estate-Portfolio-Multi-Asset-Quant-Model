import {API, STATIC_DEMO} from './config';

/** Read-only transport for GitHub Pages. POST never pretends to run a model. */
export function installStaticApi() {
  if (!STATIC_DEMO) return;
  const networkFetch = window.fetch.bind(window);
  const apiUrl = new URL(API, window.location.href);
  const basePath = apiUrl.pathname.replace(/\/$/, '');
  let snapshot: Promise<Record<string, any>> | undefined;
  const load = () => snapshot ??= networkFetch(import.meta.env.BASE_URL + 'data/api_snapshot.json')
    .then(async response => {
      if (!response.ok) throw new Error('Saved dashboard data is unavailable. Please reload after deployment finishes.');
      const payload = await response.json();
      return payload.routes;
    }).catch(error => {snapshot = undefined; throw error;});
  const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), {
    status, headers: {'Content-Type': 'application/json', 'X-Dashboard-Data': 'saved-public-snapshot'},
  });
  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const requestUrl = new URL(input instanceof Request ? input.url : String(input), window.location.href);
    if (requestUrl.origin !== apiUrl.origin || !requestUrl.pathname.startsWith(basePath + '/')) {
      return networkFetch(input, init);
    }
    const method = (init?.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
    if (method !== 'GET') return json({detail: 'Live calculations require the hosted backend. GitHub Pages displays saved results.'}, 405);
    const path = requestUrl.pathname.slice(basePath.length);
    if (path === '/decisions' || path.startsWith('/reviews')) return json({detail: 'Private review and decision records are unavailable in this public demonstration.'}, 403);
    try {
      const routes = await load();
      let key = path;
      if (path.startsWith('/zoning/map/')) key += '?radius_m=' + (requestUrl.searchParams.get('radius_m') || '750');
      if (!(key in routes)) return json({detail: 'This result is not included in the saved public snapshot.'}, 404);
      let body = routes[key];
      if (path === '/portfolio') {
        const country = requestUrl.searchParams.get('country');
        const search = requestUrl.searchParams.get('search')?.toLowerCase();
        let assets = body.assets.filter((asset: any) => (!country || asset.country?.toLowerCase() === country.toLowerCase()) && (!search || JSON.stringify([asset.name, asset.address, asset.segments]).toLowerCase().includes(search)));
        const limit = Number(requestUrl.searchParams.get('limit') || 500);
        assets = assets.slice(0, Number.isFinite(limit) ? Math.max(0, limit) : 500);
        body = {...body, assets, summary: {...body.summary, assets: assets.length}};
      }
      return json(body);
    } catch (error) {
      return json({detail: error instanceof Error ? error.message : 'Could not load saved results.'}, 503);
    }
  };
}
