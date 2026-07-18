import { useEffect, useState } from "react";
import { Archive, MessageSquare, Plus, Send } from "lucide-react";
import { api } from "../api";
import ApplyPanel from "../components/ApplyPanel";

type Summary = { id: string; title: string; status: string };
type Chat = {
  id: string;
  title: string;
  work: string;
  status: string;
  messages: Array<{
    id: string;
    role: string;
    content: string;
    suggestionId: string | null;
  }>;
};

export default function StoryChat() {
  const [sessions, setSessions] = useState<Summary[]>([]),
    [chat, setChat] = useState<Chat | null>(null),
    [message, setMessage] = useState(""),
    [sending, setSending] = useState(false),
    [apply, setApply] = useState<{ id: string; text: string } | null>(null);
  const refresh = () =>
    api<{ sessions: Summary[] }>("/chat/").then((x) => setSessions(x.sessions));
  useEffect(() => {
    refresh();
  }, []);
  async function create() {
    const result = await api<Chat>("/chat/", { method: "POST" });
    setChat(result);
    refresh();
  }
  async function open(id: string) {
    setChat(await api(`/chat/${id}/`));
  }
  async function send() {
    if (!chat || !message.trim()) return;
    setSending(true);
    try {
      setChat(
        await api(`/chat/${chat.id}/messages/`, {
          method: "POST",
          body: JSON.stringify({ content: message }),
        }),
      );
      setMessage("");
      refresh();
    } finally {
      setSending(false);
    }
  }
  async function archive() {
    if (!chat) return;
    setChat(
      await api(`/chat/${chat.id}/`, {
        method: "PATCH",
        body: JSON.stringify({
          status: chat.status === "active" ? "archived" : "active",
        }),
      }),
    );
    refresh();
  }
  return (
    <div className="chat-page">
      <aside className="chat-sessions">
        <header>
          <p className="eyebrow">Saved sessions</p>
          <h1>Story Chat</h1>
        </header>
        <button className="primary-button" onClick={create}>
          <Plus />
          New Conversation
        </button>
        <div className="chat-session-list">
          {sessions.map((s) => (
            <button
              className={chat?.id === s.id ? "active" : ""}
              onClick={() => open(s.id)}
              key={s.id}
            >
              <b>{s.title}</b>
              <small>{s.status}</small>
            </button>
          ))}
        </div>
      </aside>
      <section className="chat-conversation">
        {chat ? (
          <>
            <div className="chat-context">
              <div>
                <p className="eyebrow">Current context</p>
                <b>{chat.work} · World Bible · Voice Profile</b>
              </div>
              <button className="secondary-button" onClick={archive}>
                <Archive />
                {chat.status === "active" ? "Archive" : "Restore"}
              </button>
            </div>
            <div className="message-history">
              {chat.messages.map((m) => (
                <article className={`chat-message ${m.role}`} key={m.id}>
                  <p className="eyebrow">
                    {m.role === "author" ? "You" : "Story Engine"}
                  </p>
                  <div>{m.content}</div>
                  {m.suggestionId && (
                    <button
                      className="text-button"
                      onClick={() =>
                        setApply({ id: m.suggestionId!, text: m.content })
                      }
                    >
                      Apply to Story →
                    </button>
                  )}
                </article>
              ))}
            </div>
            <form
              className="chat-composer"
              onSubmit={(e) => {
                e.preventDefault();
                send();
              }}
            >
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="Ask about your story…"
                aria-label="Message"
              />
              <button
                className="primary-button"
                disabled={!message.trim() || sending}
              >
                <Send />
                {sending ? "Thinking…" : "Send"}
              </button>
            </form>
          </>
        ) : (
          <div className="chat-empty">
            <MessageSquare />
            <h2>Talk through the story</h2>
            <p>
              Start or reopen a conversation. Story Chat keeps its Work,
              context, and responses together.
            </p>
            <button className="primary-button" onClick={create}>
              Start a Conversation
            </button>
          </div>
        )}
      </section>
      {apply && (
        <ApplyPanel
          suggestionId={apply.id}
          text={apply.text}
          onClose={() => setApply(null)}
        />
      )}
    </div>
  );
}
