import { useEffect, useState } from "react";
import { ChevronLeft, User } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import CharacterActions from "../components/CharacterActions";
const sections = [
  "overview",
  "appearance",
  "personality",
  "backstory",
  "abilities",
  "bio-arcane",
  "relationships",
  "arc-notes",
  "progression",
  "evaluation",
  "appearances",
];
const labels: Record<string, string> = {
  overview: "Overview",
  appearance: "Appearance",
  personality: "Personality",
  backstory: "Backstory",
  abilities: "Abilities",
  "bio-arcane": "Bio-Arcane",
  relationships: "Relationships",
  "arc-notes": "Arc Notes",
  progression: "Progression",
  evaluation: "Evaluation",
  appearances: "Appearances",
};
const sectionFields: Record<string, string[]> = {
  overview: [
    "name",
    "aliases",
    "role",
    "age",
    "status",
    "tags",
    "summary",
    "goals",
    "internal_conflict",
    "external_conflict",
    "current_story_function",
  ],
  appearance: [
    "appearance",
    "distinctive_features",
    "clothing",
    "mannerisms",
    "sensory_presence",
  ],
  personality: [
    "personality",
    "temperament",
    "values",
    "fears",
    "wants",
    "contradictions",
    "habits",
  ],
  backstory: ["backstory", "origins", "formative_events"],
  "arc-notes": [
    "intended_arc",
    "current_arc_phase",
    "arc_turning_points",
    "arc_questions",
    "arc_predictions",
  ],
  evaluation: ["evaluation_notes"],
};
type Data = {
  id: string;
  name: string;
  status: string;
  fields: Record<string, string>;
  traits: any[];
  abilities: any[];
  relationships: any[];
  families: any[];
  groups: any[];
  mechanics: any[];
  appearances: any[];
};
function Field({
  name,
  value,
  onChange,
}: {
  name: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const label = name
    .replaceAll("_", " ")
    .replace(/\b\w/g, (x) => x.toUpperCase());
  return (
    <label>
      {label}
      <textarea
        rows={name === "summary" ? 4 : 3}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
export default function CharacterWorkspace() {
  const { id, section = "overview" } = useParams();
  const [data, setData] = useState<Data | null>(null),
    [dirty, setDirty] = useState(false),
    [borrowMembership, setBorrowMembership] = useState<string | null>(null);
  const nav = useNavigate();
  const load = () => api<Data>(`/characters/${id}/`).then(setData);
  useEffect(() => {
    load();
  }, [id]);
  if (!data) return <div className="page loading">Loading…</div>;
  const visible = sections.filter(
    (s) => s !== "bio-arcane" || data.mechanics.length,
  );
  function update(field: string, value: string) {
    setData({
      ...data,
      fields: { ...data.fields, [field]: value },
      name: field === "name" ? value : data.name,
    });
    setDirty(true);
  }
  async function save() {
    const fields = Object.fromEntries(
      Object.keys(data.fields).map((k) => [k, data.fields[k]]),
    );
    setData(
      await api(`/characters/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(fields),
      }),
    );
    setDirty(false);
  }
  return (
    <div className="character-workspace">
      <header className="character-header">
        <Link to="/characters" className="icon-link">
          <ChevronLeft />
        </Link>
        <div className="portrait-placeholder">
          <User />
        </div>
        <div className="character-identity">
          <p className="eyebrow">Character dossier</p>
          <h1>{data.name}</h1>
          <span>{data.status}</span>
        </div>
        <div className="character-actions">
          <span className="save-state">
            {dirty ? "Unsaved changes" : "Saved"}
          </span>
          <CharacterActions characterId={id!} onApplied={load} />
          <button className="primary-button" onClick={save} disabled={!dirty}>
            Save
          </button>
        </div>
      </header>
      <nav className="character-tabs" aria-label="Character sections">
        {visible.map((s) => (
          <button
            className={section === s ? "active" : ""}
            onClick={() => nav(`/characters/${id}/${s}`)}
            key={s}
          >
            {labels[s]}
          </button>
        ))}
      </nav>
      <main className="character-section">
        <div className="section-intro">
          <p className="eyebrow">{labels[section]}</p>
          <h2>
            {section === "overview"
              ? "Identity and current story function"
              : labels[section]}
          </h2>
        </div>
        {sectionFields[section]?.map((f) => (
          <Field
            key={f}
            name={f}
            value={data.fields[f]}
            onChange={(v) => update(f, v)}
          />
        ))}
        {section === "personality" && (
          <div className="record-grid">
            {data.traits.map((x) => (
              <article className="record-card" key={x.id}>
                <h3>{x.name}</h3>
                <div className="slider-track">
                  <span style={{ left: `${(x.score + 5) * 10}%` }} />
                </div>
                <small>
                  {x.low} ← {x.score} → {x.high}
                </small>
              </article>
            ))}
          </div>
        )}
        {section === "abilities" && (
          <div className="record-grid">
            {data.abilities.map((x) => (
              <article className="record-card" key={x.id}>
                <h3>{x.name}</h3>
                <p>{x.description}</p>
                <dl>
                  <dt>Mastery</dt>
                  <dd>{x.mastery}</dd>
                  <dt>Limits</dt>
                  <dd>{x.limitations || "Not set"}</dd>
                  <dt>Cost</dt>
                  <dd>{x.costs || "Not set"}</dd>
                </dl>
                {x.stages.map((s: any) => (
                  <span className="badge" key={s.name}>
                    {s.name} · {s.state}
                  </span>
                ))}
              </article>
            ))}
          </div>
        )}
        {section === "relationships" && (
          <>
            <div className="section-actions">
              <Link className="secondary-button" to="/web">
                Open Relationship Web
              </Link>
            </div>
            <div className="record-grid">
              {data.relationships.map((x) => (
                <Link
                  className="record-card"
                  to={`/characters/${x.otherId}/relationships`}
                  key={x.id}
                >
                  <h3>{x.other}</h3>
                  <p>
                    {x.type} · {x.status}
                  </p>
                  <small>{x.summary}</small>
                </Link>
              ))}
            </div>
          </>
        )}
        {section === "bio-arcane" &&
          data.mechanics.map((m) => (
            <div className="mechanic-layout" key={m.id}>
              <article className="record-card designation">
                <p className="eyebrow">{m.designationLabel}</p>
                <h2>
                  {m.designation} · {data.name}
                </h2>
                <p>{m.family}</p>
              </article>
              <article className="record-card">
                <h3>Shared Abilities</h3>
                {m.shared.map((a: any) => (
                  <div key={a.name}>
                    <b>{a.name}</b>
                    <p>{a.description}</p>
                    <small>{a.limitations}</small>
                  </div>
                ))}
                <h3>Borrowing Rules</h3>
                <p>{m.rules}</p>
              </article>
              <article className="record-card span-two">
                <div className="panel-title">
                  <h3>Borrowed Ability Log</h3>
                  <button
                    className="primary-button"
                    onClick={() => setBorrowMembership(m.id)}
                  >
                    Log Borrow
                  </button>
                </div>
                {m.logs.map((x: any) => (
                  <div className="log-row" key={x.id}>
                    <b>{x.ability}</b>
                    <span>from {x.from}</span>
                    <span>
                      {x.chapter}
                      {x.scene ? ` · ${x.scene}` : ""}
                    </span>
                    <span>{x.cost}</span>
                    <small>{x.consequence}</small>
                    <button
                      className="text-button"
                      onClick={async () => {
                        if (!confirm("Remove this borrowing entry?")) return;
                        await api(
                          `/characters/${id}/mechanics/${m.id}/borrow/${x.id}/`,
                          { method: "DELETE" },
                        );
                        load();
                      }}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </article>
            </div>
          ))}
        {section === "progression" && (
          <div className="record-grid">
            {data.abilities.flatMap((a) =>
              a.stages.map((s: any) => (
                <article className="record-card" key={`${a.id}-${s.name}`}>
                  <p className="eyebrow">{a.name}</p>
                  <h3>{s.name}</h3>
                  <span className="badge">{s.state}</span>
                </article>
              )),
            )}
          </div>
        )}
        {section === "appearances" && (
          <div className="appearance-list">
            {data.appearances.map((x) => (
              <a href={`/scenes/${x.id}/`} className="log-row" key={x.id}>
                <b>{x.scene}</b>
                <span>{x.chapter}</span>
                <span>{x.work}</span>
                {x.pov && <span className="badge">POV</span>}
              </a>
            ))}
          </div>
        )}
        {["overview", "relationships"].includes(section) && (
          <div className="membership-panels">
            <article className="record-card">
              <h3>Family</h3>
              {data.families.map((x) => (
                <a href={`/characters/groups/${x.id}/`} key={x.id}>
                  {x.name} · {x.role}
                </a>
              ))}
            </article>
            <article className="record-card">
              <h3>Groups & Factions</h3>
              {data.groups.map((x) => (
                <a href={`/characters/groups/${x.id}/`} key={x.id}>
                  {x.name} · {x.role}
                </a>
              ))}
            </article>
          </div>
        )}
      </main>
      {borrowMembership && (
        <BorrowModal
          characterId={id!}
          membershipId={borrowMembership}
          onClose={() => setBorrowMembership(null)}
          onSaved={() => {
            setBorrowMembership(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function BorrowModal({
  characterId,
  membershipId,
  onClose,
  onSaved,
}: {
  characterId: string;
  membershipId: string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [choices, setChoices] = useState<any>(null),
    [form, setForm] = useState<Record<string, string>>({});
  useEffect(() => {
    api(`/characters/${characterId}/mechanics/${membershipId}/borrow/`).then(
      setChoices,
    );
  }, [characterId, membershipId]);
  const source = choices?.characters.find(
    (x: any) => x.id === form.borrowedFrom,
  );
  const chapter = choices?.chapters.find((x: any) => x.id === form.chapter);
  const set = (name: string, value: string) =>
    setForm({ ...form, [name]: value });
  async function save() {
    await api(`/characters/${characterId}/mechanics/${membershipId}/borrow/`, {
      method: "POST",
      body: JSON.stringify(form),
    });
    onSaved();
  }
  return (
    <div
      className="modal-layer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="borrow-title"
    >
      <div className="modal borrow-modal">
        <h2 id="borrow-title">Log Borrowed Ability</h2>
        {!choices ? (
          <p>Loading…</p>
        ) : (
          <div className="form-grid two-column">
            <label>
              Borrowed from
              <select
                value={form.borrowedFrom || ""}
                onChange={(e) => set("borrowedFrom", e.target.value)}
              >
                <option value="">Choose Character</option>
                {choices.characters.map((x: any) => (
                  <option value={x.id} key={x.id}>
                    {x.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Ability
              <select
                value={form.ability || ""}
                onChange={(e) => {
                  setForm({
                    ...form,
                    ability: e.target.value,
                    abilityName:
                      source?.abilities.find(
                        (a: any) => a.id === e.target.value,
                      )?.name || "",
                  });
                }}
              >
                <option value="">Enter manually</option>
                {source?.abilities.map((x: any) => (
                  <option value={x.id} key={x.id}>
                    {x.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Ability name
              <input
                value={form.abilityName || ""}
                onChange={(e) => set("abilityName", e.target.value)}
              />
            </label>
            <label>
              Chapter
              <select
                value={form.chapter || ""}
                onChange={(e) =>
                  setForm({ ...form, chapter: e.target.value, scene: "" })
                }
              >
                <option value="">No Chapter</option>
                {choices.chapters.map((x: any) => (
                  <option value={x.id} key={x.id}>
                    {x.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Scene
              <select
                value={form.scene || ""}
                onChange={(e) => set("scene", e.target.value)}
              >
                <option value="">No Scene</option>
                {chapter?.scenes.map((x: any) => (
                  <option value={x.id} key={x.id}>
                    {x.title}
                  </option>
                ))}
              </select>
            </label>
            {[
              ["storyTime", "Story time"],
              ["duration", "Duration"],
              ["cost", "Cost or damage"],
              ["reducedEffectiveness", "Reduced effectiveness"],
              ["limitation", "Limitation triggered"],
              ["recovery", "Recovery"],
              ["consequence", "Lasting consequence"],
              ["continuity", "Continuity implications"],
              ["notes", "Notes"],
            ].map(([name, label]) => (
              <label key={name}>
                {label}
                <textarea
                  rows={2}
                  value={form[name] || ""}
                  onChange={(e) => set(name, e.target.value)}
                />
              </label>
            ))}
          </div>
        )}
        <div className="button-row">
          <button className="secondary-button" onClick={onClose}>
            Cancel
          </button>
          <button
            className="primary-button"
            disabled={!form.borrowedFrom || !form.abilityName}
            onClick={save}
          >
            Save Borrow
          </button>
        </div>
      </div>
    </div>
  );
}
