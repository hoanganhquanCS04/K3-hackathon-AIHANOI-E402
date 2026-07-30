import { useEffect, useState, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { api, SessionMeta } from "../lib/api";
import { SlideFrame } from "../components/SlideFrame";
import { ChatPanel } from "../components/ChatPanel";
import { SidebarStatus } from "../components/SidebarStatus";

const POOL: Record<number, string> = {
  1: "var(--image-cover-1)",
  2: "var(--image-cover-2)",
  3: "var(--image-cover-3)",
  4: "var(--image-cover-7)",
  5: "var(--image-cover-8)",
  6: "var(--image-cover-9)",
};

// Chọn ảnh theo id buổi — ổn định qua các lần render.
function pickImage(id: string): string {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0;
  return POOL[(h % 6) + 1] ?? POOL[1];
}

const STORAGE_KEY = "vlearn.session.sidebar";

function readSidebarState(): "open" | "closed" {
  if (typeof window === "undefined") return "open";
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "closed" ? "closed" : "open";
  } catch {
    return "open";
  }
}

function writeSidebarState(s: "open" | "closed") {
  try { localStorage.setItem(STORAGE_KEY, s); } catch {}
}

// Single chapter viewer — long document applied at chapter level:
// slide occupies reading column, chat occupies annotations rail.
export function SessionPage() {
  const { sid } = useParams<{ sid: string }>();
  const [session, setSession] = useState<SessionMeta | null>(null);
  const [slidePart, setSlidePart] = useState(1);
  const [done, setDone] = useState<Record<number, boolean>>({});
  const [err, setErr] = useState<string | null>(null);
  const [lookupCount, setLookupCount] = useState(0);
  const [sidebarState, setSidebarState] = useState<"open" | "closed">(() => readSidebarState());
  const chatRef = useRef<{ send: (q: string) => void } | null>(null);

  useEffect(() => {
    if (!sid) return;
    setSession(null);
    setDone({});
    setSlidePart(1);
    api.session(sid).then(setSession).catch((e) => setErr(String(e)));
  }, [sid]);

  useEffect(() => {
    writeSidebarState(sidebarState);
  }, [sidebarState]);

  // Đồng bộ phím tắt Ctrl+B / Cmd+B — native apps đều làm vậy.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "b") {
        e.preventDefault();
        setSidebarState((s) => (s === "open" ? "closed" : "open"));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (err) return <p style={{ color: "var(--color-error)", padding: "var(--space-7)" }}>Lỗi: {err}</p>;
  if (!session) return <p style={{ padding: "var(--space-9)" }}>Đang mở buổi…</p>;

  const part = session.parts[slidePart - 1];
  const nDone = Object.values(done).filter(Boolean).length;
  const bannerImg = pickImage(session.id);

  return (
    <div
      className="session-shell"
      style={{ "--sidebar-w": sidebarState === "open" ? "320px" : "56px" } as React.CSSProperties}
    >
      <main className="session-main">
        <div className="session-toolbar">
          <Link to="/" className="session-breadcrumb">
            <span className="session-breadcrumb-glyph" aria-hidden="true">←</span>
            Mục lục buổi học
          </Link>
        </div>

        <section
          className="session-banner"
          style={{ "--image-cover": bannerImg } as React.CSSProperties}
        >
          <span className="eyebrow">Buổi {session.id}</span>
          <h1>{session.title}</h1>
          <div className="session-banner-meta">
            <span className="session-banner-meta-item">
              <strong>{session.parts.length}</strong> phần
            </span>
            <span className="session-banner-meta-item">
              <strong>{session.n_sections}</strong> mục nhỏ
            </span>
            <span className="session-banner-meta-item">
              <strong>{session.n_segments}</strong> đoạn
            </span>
          </div>
        </section>

        <div className="reader-grid">
          <section>
            <SlideFrame session={session} part={part} />
            <PartOutline
              parts={session.parts}
              slidePart={slidePart}
              done={done}
              onJump={(i) => setSlidePart(i)}
              onAsk={(q) => chatRef.current?.send(q)}
            />
          </section>

          <aside className="chat-column">
            <ChatPanel
              ref={chatRef}
              session={session}
              slidePart={slidePart}
              onSlideJump={(i) => setSlidePart(i)}
              onMarkDone={(i) => setDone((d) => ({ ...d, [i]: true }))}
              onLookupCount={setLookupCount}
            />
          </aside>
        </div>
      </main>

      <SidebarStatus
        nDone={nDone}
        total={session.parts.length}
        lookupCount={lookupCount}
        state={sidebarState}
        onToggle={(next) => setSidebarState(next)}
      />
    </div>
  );
}

function PartOutline({
  parts,
  slidePart,
  done,
  onJump,
  onAsk,
}: {
  parts: SessionMeta["parts"];
  slidePart: number;
  done: Record<number, boolean>;
  onJump: (i: number) => void;
  onAsk: (q: string) => void;
}) {
  return (
    <section style={{ marginTop: "var(--space-7)" }}>
      <span className="eyebrow">Mục lục buổi học</span>
      <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {parts.map((p) => {
          const isCurrent = p.idx === slidePart;
          const isDone = done[p.idx];
          return (
            <li
              key={p.idx}
              style={{
                borderTop: "var(--rule)",
                padding: "var(--space-4) 0",
                display: "grid",
                gridTemplateColumns: "auto 1fr auto",
                gap: "var(--space-4)",
                alignItems: "center",
                minWidth: 0,
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  color: isCurrent ? "var(--color-crimson)" : "var(--color-muted)",
                  fontWeight: 500,
                  minWidth: 28,
                }}
              >
                {String(p.idx).padStart(2, "0")}
                {isDone ? " ✓" : ""}
              </span>
              <div style={{ minWidth: 0 }}>
                <button
                  onClick={() => onJump(p.idx)}
                  className="btn"
                  style={{
                    background: "transparent",
                    border: "none",
                    padding: 0,
                    fontWeight: 600,
                    color: "var(--color-ink)",
                    textAlign: "left",
                    fontSize: "1rem",
                    overflowWrap: "anywhere",    /* gate 51 */
                    minWidth: 0,
                  }}
                >
                  {p.title}
                </button>
                <p
                  style={{
                    margin: 0,
                    fontSize: "var(--text-micro)",
                    color: "var(--color-muted)",
                  }}
                >
                  {p.section_titles.length} mục · {p.n_segments} đoạn
                  {p.activity_heavy && " · chủ yếu hoạt động lớp"}
                </p>
              </div>
              <button
                onClick={() => onAsk(`tóm phần ${p.idx}`)}
                className="btn btn-primary"
                style={{ fontSize: "var(--text-micro)", padding: "var(--space-1) var(--space-3)" }}
              >
                Tóm
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
