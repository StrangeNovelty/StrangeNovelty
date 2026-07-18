import { useState } from "react";
import { api } from "../api";

const destinations = [
  ["world_bible", "World Bible"],
  ["codex", "Codex"],
  ["character_note", "Character Note"],
  ["chapter_outline", "Chapter Outline"],
  ["plot_thread", "Plot Thread"],
  ["location", "Location"],
  ["item", "Item"],
];

export default function ApplyPanel({
  suggestionId,
  text,
  onClose,
  targetCharacterId,
}: {
  suggestionId: string;
  text: string;
  onClose: () => void;
  targetCharacterId?: string;
}) {
  const [destination, setDestination] = useState("world_bible");
  const [title, setTitle] = useState("New story element");
  const [content, setContent] = useState(text);
  const [result, setResult] = useState<{ label: string; url: string } | null>(
    null,
  );
  async function apply() {
    setResult(
      await api(`/suggestions/${suggestionId}/apply/`, {
        method: "POST",
        body: JSON.stringify({
          destination,
          title,
          content,
          targetId: targetCharacterId,
        }),
      }),
    );
  }
  return (
    <div
      className="modal-layer"
      role="dialog"
      aria-modal="true"
      aria-labelledby="apply-title"
    >
      <div className="modal apply-modal">
        <h2 id="apply-title">Apply to Story</h2>
        <p>
          Review the destination and content. Nothing changes until you confirm.
        </p>
        <label>
          Destination
          <select
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
          >
            {destinations
              .filter(([v]) => v !== "character_note" || targetCharacterId)
              .map(([v, l]) => (
                <option value={v} key={v}>
                  {l}
                </option>
              ))}
          </select>
        </label>
        <label>
          Title
          <input value={title} onChange={(e) => setTitle(e.target.value)} />
        </label>
        <label>
          Content
          <textarea
            rows={12}
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />
        </label>
        {result ? (
          <div className="success-panel">
            Created <a href={result.url}>{result.label}</a>.
          </div>
        ) : (
          <div className="button-row">
            <button className="secondary-button" onClick={onClose}>
              Cancel
            </button>
            <button className="primary-button" onClick={apply}>
              Confirm Apply
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
