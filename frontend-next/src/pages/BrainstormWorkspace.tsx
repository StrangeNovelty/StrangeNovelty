import { useEffect, useState } from "react";
import { ChevronLeft, Plus, RotateCcw, Sparkles, X } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import ApplyPanel from "../components/ApplyPanel";

type Card = { id: string; label: string; category: string; manual?: boolean };
type Character = { id: string; name: string };
type Category = { id: string; name: string };
type Session = {
  id: string;
  title: string;
  mode: string;
  modes: Array<{ value: string; label: string }>;
  cards: Card[];
  characters: Character[];
  selectedCharacterIds: string[];
  categories: Category[];
  focus: string;
  exclusions: string;
  authorNotes: string;
  result: null | { id: string; text: string; state: string };
  providerAvailable: boolean;
};

export default function BrainstormWorkspace() {
  const { id } = useParams();
  const [data, setData] = useState<Session | null>(null);
  const [drawOpen, setDrawOpen] = useState(false);
  const [categories, setCategories] = useState<string[]>([]);
  const [manual, setManual] = useState("");
  const [apply, setApply] = useState(false);
  const [generating, setGenerating] = useState(false);
  const load = () => api<Session>(`/brainstorm/${id}/`).then(setData);
  useEffect(() => {
    load();
  }, [id]);
  if (!data) return <div className="page loading">Loading…</div>;
  async function patch(values: Record<string, unknown>) {
    setData(
      await api(`/brainstorm/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(values),
      }),
    );
  }
  async function draw(count: number) {
    setData(
      await api(`/brainstorm/${id}/draw/`, {
        method: "POST",
        body: JSON.stringify({ count, categories }),
      }),
    );
    setDrawOpen(false);
  }
  async function addManual() {
    if (!manual.trim()) return;
    setData(
      await api(`/brainstorm/${id}/cards/`, {
        method: "POST",
        body: JSON.stringify({ text: manual }),
      }),
    );
    setManual("");
  }
  async function removeCard(cardId: string) {
    setData(
      await api(`/brainstorm/${id}/cards/${cardId}/`, { method: "DELETE" }),
    );
  }
  async function generate() {
    setGenerating(true);
    try {
      setData(await api(`/brainstorm/${id}/generate/`, { method: "POST" }));
    } finally {
      setGenerating(false);
    }
  }
  const modeName = data.modes.find((x) => x.value === data.mode)?.label;
  return (
    <div className="brainstorm-page">
      <header className="workspace-header">
        <Link to="/brainstorm" className="icon-link">
          <ChevronLeft />
        </Link>
        <div>
          <p className="eyebrow">Brainstorm session</p>
          <input
            className="title-input"
            aria-label="Session title"
            value={data.title}
            onBlur={(e) => patch({ title: e.target.value })}
            onChange={(e) => setData({ ...data, title: e.target.value })}
          />
        </div>
        <span className="save-state">Changes save automatically</span>
      </header>
      <nav className="mode-tabs" aria-label="Generator mode">
        {data.modes.map((mode) => (
          <button
            className={data.mode === mode.value ? "active" : ""}
            onClick={() => patch({ mode: mode.value })}
            key={mode.value}
          >
            {mode.label}
          </button>
        ))}
      </nav>
      <div className="brainstorm-split">
        <section className="brainstorm-inputs">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Cards Drawn</p>
              <h2>Creative ingredients</h2>
            </div>
            <button
              className="secondary-button"
              onClick={() => setDrawOpen(true)}
            >
              <Sparkles size={15} /> Draw
            </button>
          </div>
          <div className="card-chip-list">
            {data.cards.map((card) => (
              <span className="card-chip" key={card.id}>
                <small>{card.category}</small>
                {card.label}
                <button
                  aria-label={`Remove ${card.label}`}
                  onClick={() => removeCard(card.id)}
                >
                  <X />
                </button>
              </span>
            ))}
            {!data.cards.length && (
              <p className="muted">
                Draw randomly or add a Card idea of your own.
              </p>
            )}
          </div>
          <div className="inline-add">
            <input
              value={manual}
              onChange={(e) => setManual(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && addManual()}
              placeholder="Add a card manually…"
              aria-label="Manual Card"
            />
            <button onClick={addManual} aria-label="Add manual Card">
              <Plus />
            </button>
          </div>
          <label className="field-label">Characters in This Session</label>
          <div className="choice-chips">
            {data.characters.map((c) => (
              <button
                className={
                  data.selectedCharacterIds.includes(c.id) ? "selected" : ""
                }
                onClick={() =>
                  patch({ characterId: c.id, toggleCharacter: true })
                }
                key={c.id}
              >
                {c.name}
              </button>
            ))}
            {!data.characters.length && (
              <span className="muted">
                No Characters in the active Work yet.
              </span>
            )}
          </div>
          <label>
            Keep Out
            <textarea
              rows={3}
              value={data.exclusions}
              onBlur={(e) => patch({ exclusions: e.target.value })}
              onChange={(e) => setData({ ...data, exclusions: e.target.value })}
              placeholder="Ideas, tones, or outcomes to avoid…"
            />
          </label>
          <label>
            Additional Focus
            <textarea
              rows={3}
              value={data.focus}
              onBlur={(e) => patch({ focus: e.target.value })}
              onChange={(e) => setData({ ...data, focus: e.target.value })}
              placeholder={`What should ${modeName} concentrate on?`}
            />
          </label>
          <button
            className="generate-button"
            disabled={generating || !data.providerAvailable}
            onClick={generate}
          >
            <Sparkles />
            {generating ? "Generating…" : `Generate ${modeName}`}
          </button>
          <label>
            Your Notes
            <textarea
              rows={5}
              value={data.authorNotes}
              onBlur={(e) => patch({ authorNotes: e.target.value })}
              onChange={(e) =>
                setData({ ...data, authorNotes: e.target.value })
              }
              placeholder="Keep your own thinking beside the generated result…"
            />
          </label>
        </section>
        <aside className="brainstorm-result">
          <div className="result-header">
            <div>
              <p className="eyebrow">Generated Result</p>
              <h2>{modeName}</h2>
            </div>
            {data.result && (
              <button className="secondary-button" onClick={generate}>
                <RotateCcw /> Regenerate
              </button>
            )}
          </div>
          {data.result ? (
            <>
              <textarea
                className="result-editor"
                aria-label="Generated result"
                value={data.result.text}
                onChange={(e) =>
                  setData({
                    ...data,
                    result: { ...data.result!, text: e.target.value },
                  })
                }
              />
              <div className="result-actions">
                <button
                  className="secondary-button"
                  onClick={() => patch({ reviewedOutput: data.result!.text })}
                >
                  Save Result
                </button>
                <button
                  className="primary-button"
                  onClick={() => setApply(true)}
                >
                  Apply to Story →
                </button>
              </div>
            </>
          ) : (
            <div className="result-empty">
              <Sparkles />
              <h3>Your result will stay here</h3>
              <p>
                Draw Cards, shape the focus, and generate. You can keep editing
                the same session while the result remains visible.
              </p>
            </div>
          )}
        </aside>
      </div>
      {drawOpen && (
        <div
          className="modal-layer"
          role="dialog"
          aria-modal="true"
          aria-labelledby="draw-title"
        >
          <div className="modal draw-modal">
            <button
              className="modal-close"
              onClick={() => setDrawOpen(false)}
              aria-label="Close"
            >
              <X />
            </button>
            <p className="eyebrow">Story Engine Cards</p>
            <h2 id="draw-title">How many Cards?</h2>
            <div className="draw-counts">
              {[3, 5, 7, 10].map((n) => (
                <button key={n} onClick={() => draw(n)}>
                  <b>{n}</b>
                  <span>Cards</span>
                </button>
              ))}
            </div>
            <p className="field-label">Optional categories</p>
            <div className="choice-chips">
              {data.categories.map((c) => (
                <button
                  className={categories.includes(c.id) ? "selected" : ""}
                  onClick={() =>
                    setCategories(
                      categories.includes(c.id)
                        ? categories.filter((x) => x !== c.id)
                        : [...categories, c.id],
                    )
                  }
                  key={c.id}
                >
                  {c.name}
                </button>
              ))}
            </div>
            <p className="muted">
              Leave categories unselected to draw randomly from the full
              collection.
            </p>
          </div>
        </div>
      )}
      {apply && data.result && (
        <ApplyPanel
          suggestionId={data.result.id}
          text={data.result.text}
          onClose={() => setApply(false)}
        />
      )}
    </div>
  );
}
