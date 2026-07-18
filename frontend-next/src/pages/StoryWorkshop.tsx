import { useEffect, useRef, useState } from "react";
import { BookOpen, ChevronLeft, Save, Sparkles } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api";
import ApplyPanel from "../components/ApplyPanel";
const tabs = [
  "outline",
  "draft",
  "editor",
  "links",
  "story-engine",
  "scene-brief",
  "sliders",
  "de-slop",
  "continuity",
  "polish",
  "package",
] as const;
const labels: Record<string, string> = {
  outline: "Outline",
  draft: "Draft",
  editor: "Editor ✦",
  links: "Links",
  "story-engine": "Story Engine ✦",
  "scene-brief": "Scene Brief ✦",
  sliders: "Sliders ✦",
  "de-slop": "De-Slop ✦",
  continuity: "Continuity ✦",
  polish: "Polish ✦",
  package: "Package",
};
type Data = {
  id: string;
  title: string;
  label: string;
  status: string;
  work: { id: string; title: string };
  fields: Record<string, string>;
  scenes: Array<{
    id: string;
    title: string;
    version: number;
    revisionId: string;
    content: string;
    lifecycle: string;
  }>;
  beats: any[];
  pacing: Record<string, number | null>;
  briefs: any[];
  snapshots: any[];
  threads: any[];
  publicationUrl: string;
};
function Area({
  label,
  value,
  onChange,
  rows = 5,
}: {
  label: string;
  value: string;
  onChange: (x: string) => void;
  rows?: number;
}) {
  return (
    <label>
      {label}
      <textarea
        rows={rows}
        value={value || ""}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
export default function StoryWorkshop() {
  const { id, tab = "outline" } = useParams();
  const [data, setData] = useState<Data | null>(null),
    [dirty, setDirty] = useState(false),
    [sceneIndex, setSceneIndex] = useState(0),
    [sceneDirty, setSceneDirty] = useState(false),
    [saving, setSaving] = useState(false),
    [stageResult, setStageResult] = useState<null | {
      suggestionId: string;
      text: string;
      stage: string;
    }>(null),
    [stageBusy, setStageBusy] = useState(false),
    [applyOpen, setApplyOpen] = useState(false);
  const nav = useNavigate(),
    key = useRef(crypto.randomUUID().replaceAll("-", "") + "save");
  useEffect(() => {
    api<Data>(`/story/${id}/`).then(setData);
  }, [id]);
  if (!data) return <div className="page loading">Loading…</div>;
  const scene = data.scenes[sceneIndex];
  function field(name: string, value: string) {
    setData({ ...data, fields: { ...data.fields, [name]: value } });
    setDirty(true);
  }
  async function savePlan() {
    setData(
      await api(`/story/${id}/`, {
        method: "PATCH",
        body: JSON.stringify(data.fields),
      }),
    );
    setDirty(false);
  }
  function draft(value: string) {
    const scenes = [...data.scenes];
    scenes[sceneIndex] = { ...scene, content: value };
    setData({ ...data, scenes });
    setSceneDirty(true);
  }
  async function saveScene() {
    if (!scene) return;
    setSaving(true);
    try {
      const x = await api<{
        version: number;
        revisionId: string;
        content: string;
      }>(`/scenes/${scene.id}/save/`, {
        method: "POST",
        body: JSON.stringify({
          version: scene.version,
          content: scene.content,
          idempotencyKey: key.current,
        }),
      });
      const scenes = [...data.scenes];
      scenes[sceneIndex] = { ...scene, ...x };
      setData({ ...data, scenes });
      setSceneDirty(false);
      key.current = crypto.randomUUID().replaceAll("-", "") + "save";
    } finally {
      setSaving(false);
    }
  }
  async function runStage(stage: string) {
    setStageBusy(true);
    try {
      setStageResult(
        await api(`/story/${id}/stage/`, {
          method: "POST",
          body: JSON.stringify({ stage }),
        }),
      );
    } finally {
      setStageBusy(false);
    }
  }
  function useOutline() {
    if (!stageResult) return;
    field(
      "outline",
      data.fields.outline
        ? `${data.fields.outline.trim()}\n\n${stageResult.text}`
        : stageResult.text,
    );
    setStageResult(null);
  }
  return (
    <div className="workshop">
      <header className="workshop-header">
        <Link to="/story" className="icon-link">
          <ChevronLeft />
        </Link>
        <div>
          <p className="eyebrow">{data.work.title}</p>
          <h1>{data.label || data.title}</h1>
        </div>
        <select
          value={data.status}
          onChange={(e) => {
            setData({ ...data, status: e.target.value });
            api(`/story/${id}/`, {
              method: "PATCH",
              body: JSON.stringify({ status: e.target.value }),
            });
          }}
        >
          <option value="brainstorm">Brainstorm</option>
          <option value="outlining">Outlining</option>
          <option value="drafting">Drafting</option>
          <option value="revising">Revising</option>
          <option value="polished">Polished</option>
        </select>
        <span className="save-state">
          {dirty || sceneDirty ? "Unsaved changes" : "Saved"}
        </span>
        {tab === "draft" ? (
          <button
            className="primary-button"
            onClick={saveScene}
            disabled={!sceneDirty || saving}
          >
            <Save />
            {saving ? "Saving…" : "Save Draft"}
          </button>
        ) : (
          <button
            className="primary-button"
            onClick={savePlan}
            disabled={!dirty}
          >
            <Save />
            Save
          </button>
        )}
      </header>
      <nav className="workshop-tabs">
        {tabs.map((x) => (
          <button
            className={tab === x ? "active" : ""}
            onClick={() => nav(`/story/${id}/${x}`)}
            key={x}
          >
            {labels[x]}
          </button>
        ))}
      </nav>
      <main className={`workshop-body ${tab === "draft" ? "draft-stage" : ""}`}>
        {tab === "outline" && (
          <div className="stage-grid">
            <section className="stage-panel">
              <p className="eyebrow">Intake Brief</p>
              <Area
                label="Concept"
                value={data.fields.concept}
                onChange={(x) => field("concept", x)}
              />
              <Area
                label="Key Beats"
                value={data.fields.key_beats}
                onChange={(x) => field("key_beats", x)}
              />
              <Area
                label="Emotional Arc"
                value={data.fields.emotional_arc}
                onChange={(x) => field("emotional_arc", x)}
              />
              <Area
                label="POV Notes"
                value={data.fields.character_focus}
                onChange={(x) => field("character_focus", x)}
              />
              <Area
                label="Chapter Goal"
                value={data.fields.goal}
                onChange={(x) => field("goal", x)}
              />
            </section>
            <section className="stage-panel">
              <p className="eyebrow">Brain Dump</p>
              <Area
                label="Everything on your mind"
                value={data.fields.brain_dump}
                onChange={(x) => field("brain_dump", x)}
                rows={8}
              />
              <button
                className="generate-button"
                disabled={stageBusy}
                onClick={() => runStage("outline")}
              >
                <Sparkles />
                Build Outline
              </button>
              <Area
                label="Outline"
                value={data.fields.outline}
                onChange={(x) => field("outline", x)}
                rows={15}
              />
            </section>
          </div>
        )}
        {tab === "draft" && (
          <>
            <aside className="scene-rail">
              <p className="eyebrow">Scenes</p>
              {data.scenes.map((x, i) => (
                <button
                  className={i === sceneIndex ? "active" : ""}
                  onClick={() => setSceneIndex(i)}
                  key={x.id}
                >
                  {x.title}
                  <small>Revision {x.version}</small>
                </button>
              ))}
            </aside>
            <section className="draft-canvas">
              {scene ? (
                <>
                  <div className="draft-heading">
                    <h2>{scene.title}</h2>
                    <span>Immutable Revision {scene.version}</span>
                  </div>
                  <textarea
                    value={scene.content}
                    onChange={(e) => draft(e.target.value)}
                    aria-label="Scene prose"
                  />
                </>
              ) : (
                <div className="result-empty">
                  <BookOpen />
                  <h2>Create a Scene to begin drafting</h2>
                </div>
              )}
            </section>
            <aside className="draft-context">
              <p className="eyebrow">Outline Reference</p>
              <p>{data.fields.outline || "No outline yet."}</p>
              <p className="eyebrow">Characters & Context</p>
              <p>
                Selected story context remains available to generation and
                review stages.
              </p>
            </aside>
          </>
        )}
        {tab === "editor" && (
          <Stage
            title="Editor"
            text="Analyze the current draft for prose, structure, voice, and AI-pattern concerns. Directions remain review-first."
            action="Run Editor Review"
            onAction={() => runStage("editor")}
            busy={stageBusy}
          />
        )}
        {tab === "links" && (
          <Stage
            title="Chapter Links"
            text="Connect predecessors, successors, parallels, callbacks, and consequences without changing reader order."
            action="Add Link"
          />
        )}
        {tab === "story-engine" && (
          <Stage
            title="Story Engine"
            text="Draw five Cards or add them manually, select Characters, Keep Out, and focus, then generate Chapter directions."
            action="Open Chapter Brainstorm"
          />
        )}
        {tab === "scene-brief" && (
          <div className="record-grid">
            {data.briefs.map((x) => (
              <article className="record-card" key={x.id}>
                <h3>{x.scene}</h3>
                <span className="badge">
                  {x.status}
                  {x.stale ? " · Stale" : ""}
                </span>
                <p>{x.function}</p>
                <b>Conflict</b>
                <p>{x.conflict}</p>
                <b>Stakes</b>
                <p>{x.stakes}</p>
              </article>
            ))}
            <Stage
              title="Scene Brief"
              text="Build a structured brief from intake, prior Chapter, cast, locations, world, Timeline, and open Threads."
              action="Generate Scene Brief"
              onAction={() => runStage("scene-brief")}
              busy={stageBusy}
            />
          </div>
        )}
        {tab === "sliders" && (
          <div className="slider-stage">
            {Object.entries(data.pacing).map(([k, v]) => (
              <label key={k}>
                {k.replaceAll("_", " ")}
                <input type="range" min="1" max="10" value={v || 5} />
                <b>{v || "—"}</b>
              </label>
            ))}
          </div>
        )}
        {tab === "de-slop" && (
          <Stage
            title="De-Slop"
            text="Run the desktop three-pass analysis and rewrite workflow, compare changes, then explicitly apply through an immutable Revision."
            action="Begin Pass 1"
            onAction={() => runStage("de-slop")}
            busy={stageBusy}
          />
        )}
        {tab === "continuity" && (
          <>
            <Stage
              title="Continuity"
              text="Review objective truth, reader knowledge, Character knowledge, abilities, locations, Timeline, and open Threads without mutating canon."
              action="Run Continuity Review"
              onAction={() => runStage("continuity")}
              busy={stageBusy}
            />
            <div className="record-grid">
              {data.threads.map((x) => (
                <article className="record-card" key={x.id}>
                  <h3>{x.title}</h3>
                  <span className="badge">{x.role}</span>
                </article>
              ))}
            </div>
          </>
        )}
        {tab === "polish" && (
          <Stage
            title="Polish"
            text="Produce precise line-level directions by type and location. The author controls every prose change."
            action="Run Polish Review"
            onAction={() => runStage("polish")}
            busy={stageBusy}
          />
        )}
        {tab === "package" && (
          <div className="package-stage">
            <h2>Chapter Package</h2>
            <p>
              Review the Chapter’s draft, planning, Scene Briefs, continuity
              state, and selected Revisions before publication.
            </p>
            <dl>
              <dt>Scenes</dt>
              <dd>{data.scenes.length}</dd>
              <dt>Beats</dt>
              <dd>{data.beats.length}</dd>
              <dt>Snapshots</dt>
              <dd>{data.snapshots.length}</dd>
            </dl>
            <a className="primary-button" href={data.publicationUrl}>
              Continue to Publication →
            </a>
          </div>
        )}
      </main>
      {stageResult && (
        <aside className="stage-result-panel" aria-label="AI review result">
          <div className="panel-title">
            <h2>Review Result</h2>
            <button
              className="text-button"
              onClick={() => setStageResult(null)}
            >
              Close
            </button>
          </div>
          <textarea
            aria-label="Reviewed AI output"
            value={stageResult.text}
            onChange={(e) =>
              setStageResult({ ...stageResult, text: e.target.value })
            }
          />
          <div className="button-row">
            {stageResult.stage === "outline" && (
              <button className="primary-button" onClick={useOutline}>
                Append to Outline
              </button>
            )}
            <button
              className="secondary-button"
              onClick={() => setApplyOpen(true)}
            >
              Apply to Story →
            </button>
          </div>
        </aside>
      )}
      {applyOpen && stageResult && (
        <ApplyPanel
          suggestionId={stageResult.suggestionId}
          text={stageResult.text}
          onClose={() => setApplyOpen(false)}
        />
      )}
    </div>
  );
}
function Stage({
  title,
  text,
  action,
  onAction,
  busy = false,
}: {
  title: string;
  text: string;
  action: string;
  onAction?: () => void;
  busy?: boolean;
}) {
  return (
    <section className="stage-empty">
      <Sparkles />
      <h2>{title}</h2>
      <p>{text}</p>
      <button
        className="generate-button"
        onClick={onAction}
        disabled={!onAction || busy}
      >
        {busy ? "Working…" : action}
      </button>
    </section>
  );
}
