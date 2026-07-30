import { useEffect, useState } from "react";
import { api, SessionMeta } from "../lib/api";
import { SessionCard } from "../components/SessionCard";

// Hero + grid — long document macrostructure applied at chapter-list level.
// Vertical rhythm: eyebrow → display headline → sub-copy → chapter grid.
export function HomePage() {
  const [sessions, setSessions] = useState<SessionMeta[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.outline().then(setSessions).catch((e) => setErr(String(e)));
  }, []);

  return (
    <main className="container-wide" style={{ padding: "var(--space-9) 0" }}>
      <section className="hero-cover">
        {/* Slideshow layer — 4 ảnh cross-fade. Lớp này đè dưới overlay, trên nền navy. */}
        <div className="hero-slides" aria-hidden="true">
          <div /><div /><div /><div />
        </div>

        <span className="eyebrow">VLearn · VinUni AI Thực Chiến</span>
        <h1 style={{ fontSize: "var(--text-display-xl)", marginBottom: "var(--space-4)" }}>
          Sổ tay buổi học
        </h1>
        <p style={{ fontSize: "1.15rem", margin: 0 }}>
          Nghỉ buổi hay mất mạch? Chọn buổi, tóm dần từng phần — mỗi ý đều bấm được
          về nguyên văn lời giảng.
        </p>

        {/* Stats strip — chạy stagger fade-up khi vào */}
        <div
          className="stagger hero-stats"
          aria-hidden="true"
        >
          <Stat i={0} k={statsK(sessions, 0)} label="buổi đã ghi" />
          <Stat i={1} k={statsK(sessions, 1)} label="phần bài giảng" />
          <Stat i={2} k={statsK(sessions, 2)} label="đoạn transcript" />
        </div>
      </section>

      <Banner />

      {err && <p style={{ color: "var(--color-error)" }}>Lỗi: {err}</p>}
      {!sessions && !err && <p style={{ color: "var(--color-muted)" }}>Đang tải mục lục…</p>}

      {sessions && (
        <>
          <p className="eyebrow" style={{ marginTop: "var(--space-9)" }}>
            {sessions.length} buổi đã có bản ghi
          </p>
          <h2 style={{ marginBottom: "var(--space-6)" }}>Mục lục</h2>
          <div
            className="stagger"
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 280px), 1fr))",
              gap: "var(--space-5)",
            }}
          >
            {sessions.map((s, i) => (
              <SessionCard
                key={s.id}
                session={s}
                imageIndex={(i + 1) % 6}      /* 1..6 — rotate qua pool */
                staggerIndex={i}
              />
            ))}
          </div>
        </>
      )}
    </main>
  );
}

function statsK(sessions: SessionMeta[] | null, slot: number): string {
  if (!sessions) return "—";
  if (slot === 0) return String(sessions.length);
  if (slot === 1) return String(sessions.reduce((a, s) => a + s.parts.length, 0));
  return String(sessions.reduce((a, s) => a + s.n_segments, 0));
}

function Stat({ k, label, i }: { k: string; label: string; i: number }) {
  return (
    <div className="hero-stat" style={{ "--i": i } as React.CSSProperties}>
      <span className="hero-stat-k">{k}</span>
      <span className="hero-stat-label">{label}</span>
    </div>
  );
}

function Banner() {
  return (
    <aside
      role="note"
      className="fade-up"
      style={{
        borderLeft: "3px solid var(--color-crimson)",
        background: "color-mix(in oklch, var(--color-crimson-soft) 60%, var(--color-paper))",
        padding: "var(--space-3) var(--space-4)",
        borderRadius: "var(--radius-sm)",
        fontSize: "var(--text-small)",
        color: "var(--color-ink-2)",
        maxWidth: 820,
        marginBottom: "var(--space-7)",
      }}
    >
      <strong style={{ color: "var(--color-crimson-deep)" }}>Luồng tóm tắt đã chạy thật.</strong>{" "}
      Gõ "tóm phần 1" là gọi AI ngay trên bản ghi của buổi — mọi số đọc trực tiếp từ
      transcript. Riêng luồng tra cứu <em>vẫn là chỗ trống</em>, chưa nối.
    </aside>
  );
}