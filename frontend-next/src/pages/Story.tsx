import { useEffect, useState } from "react";
import { BookOpen, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { api } from "../api";
type Ch = { id: string; title: string; status: string };
type Data = {
  work: null | { id: string; title: string };
  volumes: Array<{
    id: string;
    title: string;
    arcs: Array<{ id: string; title: string; chapters: Ch[] }>;
    chapters: Ch[];
  }>;
  unassigned: Ch[];
};
const rows = (xs: Ch[]) =>
  xs.map((x) => (
    <Link className="story-row" to={`/story/${x.id}/outline`} key={x.id}>
      <BookOpen />
      <b>{x.title}</b>
      <span className="badge">{x.status}</span>
      <ChevronRight />
    </Link>
  ));
export default function Story() {
  const [data, setData] = useState<Data | null>(null);
  useEffect(() => {
    api<Data>("/story/").then(setData);
  }, []);
  if (!data) return <div className="page loading">Loading…</div>;
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">Story</p>
          <h1>{data.work?.title || "Story Workshop"}</h1>
          <p>
            Volumes, Arcs, Chapters, and the complete Chapter production
            pipeline.
          </p>
        </div>
        <div className="button-row">
          <button className="secondary-button">Series Map</button>
          <button className="secondary-button">Pacing Map</button>
          <button className="primary-button">Add Chapter</button>
        </div>
      </header>
      <div className="hierarchy">
        {data.volumes.map((v) => (
          <section className="hierarchy-volume" key={v.id}>
            <h2>{v.title}</h2>
            {v.arcs.map((a) => (
              <div className="hierarchy-arc" key={a.id}>
                <h3>{a.title}</h3>
                {rows(a.chapters)}
              </div>
            ))}
            {rows(v.chapters)}
          </section>
        ))}
        {!!data.unassigned.length && (
          <section className="hierarchy-volume">
            <h2>Unassigned Chapters</h2>
            {rows(data.unassigned)}
          </section>
        )}
      </div>
    </div>
  );
}
