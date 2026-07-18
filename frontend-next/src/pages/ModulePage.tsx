import { useEffect, useState } from "react";
import { Plus, Search as SearchIcon } from "lucide-react";
import { api } from "../api";
type Row = {
  id: string;
  title: string;
  meta: string;
  status: string;
  body: string;
  url: string;
};
const copy: Record<
  string,
  { title: string; eyebrow: string; help: string; action: string }
> = {
  items: {
    title: "Items",
    eyebrow: "World",
    help: "Objects, artifacts, technologies, holders, locations, and Chapter appearances.",
    action: "Add Item",
  },
  timeline: {
    title: "Timeline",
    eyebrow: "World",
    help: "Events in story chronology, distinct from reader order.",
    action: "Add Event",
  },
  locations: {
    title: "Locations",
    eyebrow: "World",
    help: "Places where Scenes occur, with events, connections, and predictions.",
    action: "Create Location",
  },
  "plot-threads": {
    title: "Plot Threads",
    eyebrow: "Story",
    help: "Promises, mysteries, threats, setups, and their eventual resolution.",
    action: "Add Thread",
  },
  "voice-profile": {
    title: "Voice Profile",
    eyebrow: "Craft",
    help: "Authored samples and durable prose guidance used by creative tools.",
    action: "Add Sample",
  },
  "cross-reference": {
    title: "Cross-Reference",
    eyebrow: "Craft",
    help: "Find where Characters appear alone or together across Chapters and Scenes.",
    action: "Compare Characters",
  },
  publication: {
    title: "Publication",
    eyebrow: "Craft",
    help: "Reading copies, export history, and the publication queue.",
    action: "Compile",
  },
};
export default function ModulePage({ kind }: { kind: string }) {
  const [rows, setRows] = useState<Row[]>([]),
    [query, setQuery] = useState("");
  const c = copy[kind];
  useEffect(() => {
    api<{ rows: Row[] }>(`/modules/${kind}/`).then((x) => setRows(x.rows));
  }, [kind]);
  const shown = rows.filter((x) =>
    (x.title + x.meta + x.body).toLowerCase().includes(query.toLowerCase()),
  );
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">{c.eyebrow}</p>
          <h1>{c.title}</h1>
          <p>{c.help}</p>
        </div>
        <button className="primary-button">
          <Plus />
          {c.action}
        </button>
      </header>
      <div className="module-tools">
        <label>
          <SearchIcon />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={`Search ${c.title}…`}
          />
        </label>
      </div>
      <div className="module-list">
        {shown.map((x) => (
          <a className="record-card" href={x.url} key={x.id}>
            <div className="panel-title">
              <span>{x.title}</span>
              <span className="badge">{x.status}</span>
            </div>
            <small>{x.meta}</small>
            <p>{x.body || "No details yet."}</p>
          </a>
        ))}
      </div>
      {!shown.length && (
        <div className="empty-panel">
          <h2>No {c.title} yet</h2>
          <p>{c.help}</p>
          <button className="primary-button">{c.action}</button>
        </div>
      )}
    </div>
  );
}
