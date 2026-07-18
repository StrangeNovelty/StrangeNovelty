import { useEffect, useState } from "react";
import { Plus, User } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
type Row = {
  id: string;
  name: string;
  role: string;
  status: string;
  summary: string;
  abilities: number;
  appearances: number;
};
export default function Characters() {
  const [rows, setRows] = useState<Row[]>([]),
    [name, setName] = useState("");
  const nav = useNavigate();
  useEffect(() => {
    api<{ characters: Row[] }>("/characters/").then((x) =>
      setRows(x.characters),
    );
  }, []);
  async function create() {
    if (!name.trim()) return;
    const x = await api<{ id: string }>("/characters/", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    nav(`/characters/${x.id}/overview`);
  }
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Characters</p>
          <h1>Character Workspace</h1>
          <p>
            Long-term dossiers for cast, relationships, abilities, and story
            appearances.
          </p>
        </div>
        <div className="inline-create">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Character name"
          />
          <button className="primary-button" onClick={create}>
            <Plus />
            Create
          </button>
        </div>
      </header>
      <div className="character-grid">
        {rows.map((x) => (
          <Link
            to={`/characters/${x.id}/overview`}
            className="character-card"
            key={x.id}
          >
            <div className="portrait-placeholder">
              <User />
            </div>
            <div>
              <h2>{x.name}</h2>
              <p>
                {x.role || "Role not set"} · {x.status || "Active"}
              </p>
              <small>
                {x.abilities} abilities · {x.appearances} appearances
              </small>
              <p>
                {x.summary || "Open the dossier to develop this Character."}
              </p>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
