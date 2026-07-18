import { useEffect, useState } from "react";
import { api } from "../api";
type RecordRow = {
  id: string;
  name: string;
  status: string;
  description: string;
};
type Data = {
  factions: RecordRow[];
  codex: RecordRow[];
  regions: RecordRow[];
  locations: RecordRow[];
  items: RecordRow[];
};
const tabs = ["factions", "codex", "regions", "locations", "items"] as const;
export default function World() {
  const [data, setData] = useState<Data | null>(null),
    [tab, setTab] = useState<(typeof tabs)[number]>("factions");
  useEffect(() => {
    api<Data>("/world/").then(setData);
  }, []);
  if (!data) return <div className="page loading">Loading…</div>;
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">World</p>
          <h1>Structured World</h1>
          <p>
            Factions, Codex, geography, Locations, and Items connected to the
            story.
          </p>
        </div>
        <button className="primary-button">Add {tab.slice(0, -1)}</button>
      </header>
      <nav className="content-tabs">
        {tabs.map((x) => (
          <button
            className={tab === x ? "active" : ""}
            onClick={() => setTab(x)}
            key={x}
          >
            {x[0].toUpperCase() + x.slice(1)} <span>{data[x].length}</span>
          </button>
        ))}
      </nav>
      <div className="expandable-list">
        {data[tab].map((x) => (
          <details className="record-card" key={x.id}>
            <summary>
              <b>{x.name}</b>
              <span className="badge">{x.status}</span>
            </summary>
            <p>{x.description || "No description yet."}</p>
            <a href={`/world/${tab}/${x.id}/`}>Open full record →</a>
          </details>
        ))}
      </div>
    </div>
  );
}
