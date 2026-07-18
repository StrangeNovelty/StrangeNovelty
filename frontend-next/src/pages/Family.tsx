import { useEffect, useState } from "react";
import { Users } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api";
type FamilyRow = {
  id: string;
  name: string;
  tagline: string;
  description: string;
  history: string;
  members: Array<{ id: string; name: string; role: string; status: string }>;
};
export default function Family() {
  const [rows, setRows] = useState<FamilyRow[]>([]);
  useEffect(() => {
    api<{ families: FamilyRow[] }>("/family/").then((x) => setRows(x.families));
  }, []);
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Characters</p>
          <h1>Family</h1>
          <p>
            Shared origin, baseline traits, manifestations, bonds, and
            interactions.
          </p>
        </div>
        <button className="primary-button">Create Family</button>
      </header>
      <div className="family-grid">
        {rows.map((f) => (
          <article className="panel" key={f.id}>
            <div className="panel-title">
              <span>
                <Users />
                {f.name}
              </span>
              <span>{f.members.length} members</span>
            </div>
            <p>{f.tagline || f.description}</p>
            <div className="roster">
              {f.members.map((m) => (
                <Link to={`/characters/${m.id}/overview`} key={m.id}>
                  <b>{m.name}</b>
                  <small>{m.role || m.status}</small>
                </Link>
              ))}
            </div>
          </article>
        ))}
      </div>
      {!rows.length && (
        <div className="empty-panel">
          <h2>No Families yet</h2>
          <p>
            Create one when shared origin and inherited traits matter beyond an
            ordinary Group.
          </p>
        </div>
      )}
    </div>
  );
}
