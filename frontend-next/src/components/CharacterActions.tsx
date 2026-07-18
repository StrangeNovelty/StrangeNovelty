import { useEffect, useState } from "react";
import { Bot, Sparkles, X } from "lucide-react";
import { api } from "../api";
import ApplyPanel from "./ApplyPanel";

type Proposal = {
  proposalId: string;
  rows: Array<{
    field: string;
    label: string;
    existing: string;
    proposed: string;
  }>;
};
type Action = { key: string; label: string };

export default function CharacterActions({
  characterId,
  onApplied,
}: {
  characterId: string;
  onApplied: () => void;
}) {
  const [mode, setMode] = useState<"fill" | "assist" | null>(null),
    [description, setDescription] = useState(""),
    [proposal, setProposal] = useState<Proposal | null>(null),
    [selected, setSelected] = useState<string[]>([]),
    [actions, setActions] = useState<Action[]>([]),
    [result, setResult] = useState<{
      suggestionId: string;
      text: string;
    } | null>(null),
    [busy, setBusy] = useState(false),
    [applyOpen, setApplyOpen] = useState(false);
  useEffect(() => {
    if (mode === "assist")
      api<{ actions: Action[] }>(`/characters/${characterId}/assist/`).then(
        (x) => setActions(x.actions),
      );
  }, [mode, characterId]);
  async function generateFill() {
    setBusy(true);
    try {
      const x = await api<Proposal>(`/characters/${characterId}/fill/`, {
        method: "POST",
        body: JSON.stringify({ description }),
      });
      setProposal(x);
      setSelected(
        x.rows.filter((row) => !row.existing).map((row) => row.field),
      );
    } finally {
      setBusy(false);
    }
  }
  async function applyFill() {
    if (!proposal) return;
    await api(`/characters/${characterId}/fill/`, {
      method: "PATCH",
      body: JSON.stringify({
        proposalId: proposal.proposalId,
        fields: selected,
      }),
    });
    setMode(null);
    setProposal(null);
    onApplied();
  }
  async function assist(task: string) {
    setBusy(true);
    try {
      setResult(
        await api(`/characters/${characterId}/assist/`, {
          method: "POST",
          body: JSON.stringify({ task }),
        }),
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <button className="secondary-button" onClick={() => setMode("fill")}>
        <Sparkles />
        Fill from Description
      </button>
      <button className="secondary-button" onClick={() => setMode("assist")}>
        <Bot />
        AI Assist
      </button>
      {mode && (
        <div className="modal-layer">
          <div className="modal character-action-modal">
            <button className="modal-close" onClick={() => setMode(null)}>
              <X />
            </button>
            {mode === "fill" ? (
              <>
                <p className="eyebrow">Character tools</p>
                <h2>Fill from Description</h2>
                {proposal ? (
                  <>
                    <p>
                      Select exactly which proposed values to apply. Existing
                      fields are visible beside each proposal.
                    </p>
                    <div className="proposal-list">
                      {proposal.rows.map((row) => (
                        <label key={row.field}>
                          <input
                            type="checkbox"
                            checked={selected.includes(row.field)}
                            onChange={() =>
                              setSelected(
                                selected.includes(row.field)
                                  ? selected.filter((x) => x !== row.field)
                                  : [...selected, row.field],
                              )
                            }
                          />
                          <span>
                            <b>{row.label}</b>
                            <small>Existing: {row.existing || "Empty"}</small>
                            <p>{row.proposed}</p>
                          </span>
                        </label>
                      ))}
                    </div>
                    <button className="primary-button" onClick={applyFill}>
                      Apply Selected Fields
                    </button>
                  </>
                ) : (
                  <>
                    <p>
                      Describe the Character in your own words. Proposed values
                      remain review-first.
                    </p>
                    <textarea
                      rows={12}
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="Write a Character description…"
                    />
                    <button
                      className="generate-button"
                      disabled={!description.trim() || busy}
                      onClick={generateFill}
                    >
                      {busy ? "Analyzing…" : "Review Proposed Fields"}
                    </button>
                  </>
                )}
              </>
            ) : (
              <>
                <p className="eyebrow">Character tools</p>
                <h2>AI Assist</h2>
                {result ? (
                  <>
                    <textarea
                      className="assist-result"
                      value={result.text}
                      onChange={(e) =>
                        setResult({ ...result, text: e.target.value })
                      }
                    />
                    <button
                      className="primary-button"
                      onClick={() => setApplyOpen(true)}
                    >
                      Apply to Story →
                    </button>
                  </>
                ) : (
                  <div className="assist-actions">
                    {actions.map((action) => (
                      <button
                        disabled={busy}
                        onClick={() => assist(action.key)}
                        key={action.key}
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
      {applyOpen && result && (
        <ApplyPanel
          suggestionId={result.suggestionId}
          text={result.text}
          targetCharacterId={characterId}
          onClose={() => setApplyOpen(false)}
        />
      )}
    </>
  );
}
