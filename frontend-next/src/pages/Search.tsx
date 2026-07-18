import { FormEvent, useState } from "react";
import { Search as SearchIcon } from "lucide-react";
import { api } from "../api";
type Result = { type: string; title: string; snippet: string; url: string };
export default function Search() {
  const [q, setQ] = useState(""),
    [results, setResults] = useState<Result[]>([]),
    [searched, setSearched] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    const x = await api<{ results: Result[] }>(
      `/search/?q=${encodeURIComponent(q)}`,
    );
    setResults(x.results);
    setSearched(true);
  }
  const groups = Map.groupBy(results, (x) => x.type);
  return (
    <div className="page search-page">
      <header>
        <p className="eyebrow">Overview</p>
        <h1>Search</h1>
        <p>Find story records by the language the author uses.</p>
      </header>
      <form className="global-search" onSubmit={submit}>
        <SearchIcon />
        <input
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search the story…"
        />
        <button className="primary-button">Search</button>
      </form>
      {Array.from(groups).map(([type, rows]) => (
        <section className="search-group" key={type}>
          <h2>
            {type} <span>{rows.length}</span>
          </h2>
          {rows.map((x, i) => (
            <a href={x.url} key={`${x.url}-${i}`}>
              <b>{x.title}</b>
              <p>{x.snippet}</p>
            </a>
          ))}
        </section>
      ))}
      {searched && !results.length && (
        <div className="empty-panel">
          <h2>No story records found</h2>
          <p>Try a Character, place, Chapter, term, or Thread title.</p>
        </div>
      )}
    </div>
  );
}
