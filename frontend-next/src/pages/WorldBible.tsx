import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { api } from "../api";
type Entry = { id: string; title: string; content: string };
export default function WorldBible() {
  const [entries, setEntries] = useState<Entry[]>([]),
    [selected, setSelected] = useState<Entry | null>(null),
    [dirty, setDirty] = useState(false);
  const load = () =>
    api<{ entries: Entry[] }>("/world-bible/").then((x) => {
      setEntries(x.entries);
      if (!selected && x.entries[0]) setSelected(x.entries[0]);
    });
  useEffect(() => {
    load();
  }, []);
  async function add() {
    const x = await api<{ id: string }>("/world-bible/", {
      method: "POST",
      body: JSON.stringify({}),
    });
    await load();
    const all = await api<{ entries: Entry[] }>("/world-bible/");
    setSelected(all.entries.find((e) => e.id === x.id) || null);
  }
  async function save() {
    if (!selected) return;
    const x = await api<Entry>(`/world-bible/${selected.id}/`, {
      method: "PATCH",
      body: JSON.stringify(selected),
    });
    setSelected(x);
    setDirty(false);
    load();
  }
  async function remove() {
    if (!selected || !confirm("Delete this World Bible entry?")) return;
    await api(`/world-bible/${selected.id}/`, { method: "DELETE" });
    setSelected(null);
    load();
  }
  return (
    <div className="master-detail">
      <aside className="master-list">
        <header>
          <p className="eyebrow">World</p>
          <h1>World Bible</h1>
          <button className="primary-button" onClick={add}>
            <Plus />
            New Entry
          </button>
        </header>
        {entries.map((e) => (
          <button
            className={selected?.id === e.id ? "active" : ""}
            onClick={() => setSelected(e)}
            key={e.id}
          >
            {e.title}
          </button>
        ))}
      </aside>
      <section className="detail-editor">
        {selected ? (
          <>
            <div className="editor-toolbar">
              <span>{dirty ? "Unsaved changes" : "Saved"}</span>
              <button className="danger-button" onClick={remove}>
                <Trash2 />
                Delete
              </button>
              <button
                className="primary-button"
                onClick={save}
                disabled={!dirty}
              >
                Save
              </button>
            </div>
            <input
              className="document-title"
              value={selected.title}
              onChange={(e) => {
                setSelected({ ...selected, title: e.target.value });
                setDirty(true);
              }}
            />
            <textarea
              className="document-editor"
              value={selected.content}
              onChange={(e) => {
                setSelected({ ...selected, content: e.target.value });
                setDirty(true);
              }}
              placeholder="Write the rules, histories, cultures, cosmology, terminology, and narrative truths that shape this world…"
            />
          </>
        ) : (
          <div className="result-empty">
            <h2>Build the living World Bible</h2>
            <p>
              Free-form lore belongs here. Structured places, factions, terms,
              and objects remain in World.
            </p>
            <button className="primary-button" onClick={add}>
              Create the First Entry
            </button>
          </div>
        )}
      </section>
    </div>
  );
}
