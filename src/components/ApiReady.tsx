import {useEffect, useState, type ReactNode} from 'react';
import {API, STATIC_DEMO} from '../config';

/** Wait for a sleeping public host before mounting tabs that load API data. */
export default function ApiReady({children}: {children: ReactNode}) {
  const [ready, setReady] = useState(STATIC_DEMO);
  const [failed, setFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (STATIC_DEMO) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController | undefined;
    const started = Date.now();
    setFailed(false);
    async function check() {
      controller = new AbortController();
      const timeout = setTimeout(() => controller?.abort(), 12000);
      try {
        const response = await fetch(API + '/health', {signal: controller.signal});
        const health = response.ok ? await response.json() : null;
        if (health?.status === 'ok' && health?.portfolio_loaded && health?.results_loaded) {
          if (!cancelled) setReady(true);
          return;
        }
      } catch { /* Free hosts can take a minute to start; retry instead of mounting empty tabs. */ }
      finally { clearTimeout(timeout); }
      if (cancelled) return;
      if (Date.now() - started > 180000) setFailed(true);
      else timer = setTimeout(check, 4000);
    }
    check();
    return () => {cancelled = true; clearTimeout(timer); controller?.abort();};
  }, [retry]);
  if (ready) return children;
  return <main className="container py-5"><section className="card mx-auto" style={{maxWidth: 640}}><div className="card-body p-5">
    <h1>Portfolio intelligence</h1>
    <p role="status">{failed ? 'The dashboard service is taking longer than expected.' : 'Starting your dashboard…'}</p>
    <p>The first visit after inactivity can take a minute. This page will open automatically when the model service is ready.</p>
    {failed && <button className="btn btn-primary" onClick={() => setRetry(value => value + 1)}>Try again</button>}
  </div></section></main>;
}
