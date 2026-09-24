import { useEffect, useId, useRef, useState } from 'react';

let mermaidLoader: Promise<typeof import('mermaid').default> | null = null;

function getMermaid() {
  if (!mermaidLoader) {
    mermaidLoader = import('mermaid').then(({ default: mermaid }) => {
      mermaid.initialize({
        startOnLoad: false,
        securityLevel: 'strict',
        theme: 'base',
        themeVariables: {
          primaryColor: '#edf5ff',
          primaryTextColor: '#161616',
          primaryBorderColor: '#0f62fe',
          lineColor: '#525252',
          secondaryColor: '#d9fbfb',
          tertiaryColor: '#f4f4f4',
          fontFamily: 'IBM Plex Sans, Arial',
        },
      });

      return mermaid;
    });
  }

  return mermaidLoader;
}

export default function MermaidDiagram({
  definition,
  title,
}: {
  definition: string;
  title: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const id = useId().replaceAll(':', '');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    const renderId = `mermaid-${id}-${Math.random().toString(36).slice(2)}`;

    setError('');
    if (ref.current) {
      ref.current.innerHTML = '';
    }

    getMermaid()
      .then((mermaid) => mermaid.render(renderId, definition))
      .then(({ svg }) => {
        if (!active || !ref.current) return;
        ref.current.innerHTML = svg;
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : String(err));
        }
      });

    return () => {
      active = false;
    };
  }, [definition, id]);

  return (
    <section className="mermaid-card" aria-label={title}>
      <h2>{title}</h2>
      {error ? (
        <div className="warning">Unable to render diagram: {error}</div>
      ) : (
        <div ref={ref} className="mermaid-diagram" />
      )}
    </section>
  );
}
