import type { ReactNode } from "react";
import { useState } from "react";
import {
  BookOpen,
  Clock,
  Feather,
  Flag,
  GitMerge,
  Globe,
  Heart,
  LayoutDashboard,
  Library,
  MapPin,
  Menu,
  MessageSquare,
  Mic,
  Network,
  Search,
  Send,
  Settings,
  Shuffle,
  Sword,
  Upload,
  Users,
  X,
} from "lucide-react";
import { NavLink } from "react-router-dom";

const groups = [
  [
    "Overview",
    [
      ["/dashboard", "Dashboard", LayoutDashboard],
      ["/search", "Search", Search],
    ],
  ],
  [
    "World",
    [
      ["/world-bible", "World Bible", Library],
      ["/world", "World", Globe],
      ["/items", "Items", Sword],
      ["/timeline", "Timeline", Clock],
      ["/locations", "Locations", MapPin],
    ],
  ],
  [
    "Characters",
    [
      ["/characters", "Characters", Users],
      ["/family", "Family", Heart],
      ["/web", "Relationship Web", Network],
    ],
  ],
  [
    "Story",
    [
      ["/brainstorm", "Brainstorm", Shuffle],
      ["/plot-threads", "Plot Threads", Flag],
      ["/story", "Story Workshop", BookOpen],
    ],
  ],
  [
    "Craft",
    [
      ["/voice-profile", "Voice Profile", Mic],
      ["/cross-reference", "Cross-Reference", GitMerge],
      ["/publication", "Publication", Send],
    ],
  ],
  [
    "Tools",
    [
      ["/chat", "Story Chat", MessageSquare],
      ["/import", "Import Notes", Upload],
    ],
  ],
] as const;

export default function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="app-frame">
      <button
        className="mobile-menu"
        onClick={() => setOpen(true)}
        aria-label="Open navigation"
      >
        <Menu />
      </button>
      {open && (
        <button
          className="nav-scrim"
          onClick={() => setOpen(false)}
          aria-label="Close navigation"
        />
      )}
      <nav
        className={`sidebar ${open ? "is-open" : ""}`}
        aria-label="Story Engine"
      >
        <div className="brand">
          <span className="brand-mark">
            <Feather size={16} />
          </span>
          <span>
            <b>The Story</b>
            <b>Engine</b>
          </span>
          <button onClick={() => setOpen(false)} aria-label="Close navigation">
            <X />
          </button>
        </div>
        <div className="nav-scroll">
          {groups.map(([heading, items]) => (
            <section className="nav-group" key={heading}>
              <h2>{heading}</h2>
              {items.map(([to, label, Icon]) => (
                <NavLink
                  key={to}
                  to={to}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    isActive ? "nav-item active" : "nav-item"
                  }
                >
                  <Icon size={17} />
                  {label}
                </NavLink>
              ))}
            </section>
          ))}
        </div>
        <NavLink
          to="/settings"
          className={({ isActive }) =>
            isActive ? "nav-item settings active" : "nav-item settings"
          }
        >
          <Settings size={17} />
          Settings
        </NavLink>
      </nav>
      <main className="route-surface">{children}</main>
    </div>
  );
}
