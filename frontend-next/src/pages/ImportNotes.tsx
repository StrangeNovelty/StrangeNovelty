import { useState } from "react";
import { FileText, Sparkles } from "lucide-react";
export default function ImportNotes() {
  const [text, setText] = useState(""),
    [stage, setStage] = useState<"parse" | "review">("parse");
  return (
    <div className="page">
      <header>
        <p className="eyebrow">Tools</p>
        <h1>Import Notes</h1>
        <p>
          Parse a document, review proposed changes, then choose what enters the
          story.
        </p>
      </header>
      <div className="import-steps">
        <span className={stage === "parse" ? "active" : ""}>
          1 · Parse Document
        </span>
        <span className={stage === "review" ? "active" : ""}>2 · Review</span>
        <span>3 · Apply</span>
      </div>
      <section className="stage-panel import-panel">
        {stage === "parse" ? (
          <>
            <FileText />
            <h2>Paste or upload author notes</h2>
            <textarea
              rows={18}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste synthetic or authored notes here…"
            />
            <button
              className="generate-button"
              disabled={!text.trim()}
              onClick={() => setStage("review")}
            >
              <Sparkles />
              Parse Document
            </button>
          </>
        ) : (
          <>
            <h2>Review Proposed Changes</h2>
            <p>
              For each field, choose Keep existing, Use document, or Write my
              own. Nothing applies until final confirmation.
            </p>
            <div className="empty-panel">
              Provider parsing will populate this review.
            </div>
            <button
              className="secondary-button"
              onClick={() => setStage("parse")}
            >
              Back
            </button>
          </>
        )}
      </section>
    </div>
  );
}
