import { useEffect, useState } from "react";
import { BookOpen, ChevronRight, Flag, Globe, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api";

type DashboardData = {
  greeting: string;
  activeWork: { id: string; title: string } | null;
  chapters: Array<{ id: string; title: string; status: string; words: number }>;
  threads: Array<{ id: string; title: string; priority: string }>;
  counts: {
    characters: number;
    locations: number;
    factions: number;
    codex: number;
  };
  wordsToday: number;
  streak: number;
};

export default function Dashboard() {
  const [data, setData] = useState<DashboardData | null>(null);
  useEffect(() => {
    api<DashboardData>("/dashboard/").then(setData);
  }, []);
  if (!data) return <div className="page loading">Loading…</div>;
  return (
    <div className="page dashboard-page">
      <header>
        <p className="eyebrow">Overview</p>
        <h1>Dashboard</h1>
        <p>{data.greeting}</p>
      </header>
      <section className="dashboard-grid">
        <article className="panel span-two">
          <div className="panel-title">
            <span>
              <BookOpen /> Chapter Pipeline
            </span>
            <Link to="/story">
              Story Workshop <ChevronRight size={14} />
            </Link>
          </div>
          {data.chapters.length ? (
            data.chapters.map((ch) => (
              <Link
                className="dashboard-row"
                to={`/story/${ch.id}`}
                key={ch.id}
              >
                <span>
                  <b>{ch.title}</b>
                  <small>{ch.status}</small>
                </span>
                <span>{ch.words.toLocaleString()} words</span>
              </Link>
            ))
          ) : (
            <p className="muted">No chapters yet.</p>
          )}
        </article>
        <article className="panel">
          <div className="panel-title">
            <span>
              <Flag /> Open Threads
            </span>
          </div>
          {data.threads.length ? (
            data.threads.map((t) => (
              <Link className="dashboard-row" to="/plot-threads" key={t.id}>
                <span>
                  <b>{t.title}</b>
                  <small>{t.priority}</small>
                </span>
                <ChevronRight />
              </Link>
            ))
          ) : (
            <p className="muted">No open threads.</p>
          )}
        </article>
        <article className="panel">
          <div className="panel-title">
            <span>
              <Globe /> World at a Glance
            </span>
          </div>
          <div className="metric-grid">
            <span>
              <b>{data.counts.characters}</b>
              <small>Characters</small>
            </span>
            <span>
              <b>{data.counts.locations}</b>
              <small>Locations</small>
            </span>
            <span>
              <b>{data.counts.factions}</b>
              <small>Factions</small>
            </span>
            <span>
              <b>{data.counts.codex}</b>
              <small>Codex</small>
            </span>
          </div>
        </article>
        <article className="panel">
          <div className="panel-title">
            <span>
              <Users /> Writing Stats
            </span>
          </div>
          <div className="large-metric">
            {data.wordsToday.toLocaleString()}
            <small>words today</small>
          </div>
          <div className="large-metric small">
            {data.streak}
            <small>day streak</small>
          </div>
        </article>
        <article className="panel brainstorm-callout">
          <p className="eyebrow">Creative development</p>
          <h2>Story Engine Brainstorm</h2>
          <p>
            Draw Cards and develop a direction without leaving the workspace.
          </p>
          <Link className="primary-button" to="/brainstorm">
            Open Brainstorm
          </Link>
        </article>
      </section>
    </div>
  );
}
