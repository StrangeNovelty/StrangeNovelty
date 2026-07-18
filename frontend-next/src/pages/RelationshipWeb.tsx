import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
type Data = {
  nodes: Array<{ id: string; name: string; role: string }>;
  links: Array<{
    id: string;
    source: string;
    target: string;
    type: string;
    status: string;
  }>;
};
export default function RelationshipWeb() {
  const [data, setData] = useState<Data | null>(null);
  useEffect(() => {
    api<Data>("/relationship-web/").then(setData);
  }, []);
  if (!data) return <div className="page loading">Loading…</div>;
  const positions = new Map(
    data.nodes.map((n, i) => [
      n.id,
      { x: 50 + 38 * (i % 5), y: 45 + 34 * Math.floor(i / 5) },
    ]),
  );
  return (
    <div className="page graph-page">
      <header>
        <p className="eyebrow">Characters</p>
        <h1>Relationship Web</h1>
        <p>
          See the cast as a living network; select any Character to open the
          dossier.
        </p>
      </header>
      <div className="relationship-canvas">
        <svg
          viewBox={`0 0 250 ${Math.max(180, 80 + 34 * Math.ceil(data.nodes.length / 5))}`}
          aria-label="Character relationship graph"
        >
          {data.links.map((l) => {
            const a = positions.get(l.source),
              b = positions.get(l.target);
            return a && b ? (
              <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} key={l.id} />
            ) : null;
          })}
        </svg>
        {data.nodes.map((n) => {
          const p = positions.get(n.id)!;
          return (
            <Link
              className="graph-node"
              style={{ left: `${p.x / 2.5}%`, top: `${p.y}px` }}
              to={`/characters/${n.id}/relationships`}
              key={n.id}
            >
              <b>{n.name}</b>
              <small>{n.role}</small>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
