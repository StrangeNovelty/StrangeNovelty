import { useEffect, useState } from "react";
import { Plus, Sparkles } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";

type Session = {
  id: string;
  title: string;
  modeLabel: string;
  updatedAt: string;
  hasResult: boolean;
};

export default function BrainstormList() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const navigate = useNavigate();
  useEffect(() => {
    api<{ sessions: Session[] }>("/brainstorm/").then((x) =>
      setSessions(x.sessions),
    );
  }, []);
  async function create() {
    const result = await api<{ id: string }>("/brainstorm/", {
      method: "POST",
      body: JSON.stringify({ mode: "plot" }),
    });
    navigate(`/brainstorm/${result.id}`);
  }
  return (
    <div className="page list-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Story</p>
          <h1>Brainstorm</h1>
          <p>
            Develop ideas with Story Engine Cards and your living story context.
          </p>
        </div>
        <button className="primary-button" onClick={create}>
          <Plus size={16} /> New Brainstorm
        </button>
      </header>
      <div className="session-grid">
        {sessions.map((session) => (
          <Link
            className="session-card"
            to={`/brainstorm/${session.id}`}
            key={session.id}
          >
            <Sparkles />
            <div>
              <h2>{session.title}</h2>
              <p>{session.modeLabel}</p>
              <small>
                {session.hasResult
                  ? "Generated result ready"
                  : "Ready to develop"}{" "}
                · {session.updatedAt}
              </small>
            </div>
          </Link>
        ))}
      </div>
      {!sessions.length && (
        <div className="empty-panel">
          <Sparkles />
          <h2>Begin with a spark</h2>
          <p>
            Open a session, draw a few Cards, and develop the result without
            leaving the workspace.
          </p>
          <button className="primary-button" onClick={create}>
            Start Brainstorming
          </button>
        </div>
      )}
    </div>
  );
}
