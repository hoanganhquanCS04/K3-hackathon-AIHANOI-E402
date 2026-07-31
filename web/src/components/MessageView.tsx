import { useState } from "react";
import {
  AnswerPayload,
  Claim,
  ChatResponse,
  KeyPoint,
  PartSummary,
  RecapSummary,
} from "../lib/api";

interface ChatMsg {
  id: number;
  role: "user" | "assistant";
  body: ChatResponse | { kind: "text"; text: string };
  pending?: boolean;
}

export function MessageView({ msg }: { msg: ChatMsg }) {
  // User — bubble phải, navy
  if (msg.role === "user") {
    const text = (msg.body as { kind: "text"; text: string }).text;
    return (
      <div className="bubble bubble-user">
        <span className="bubble-avatar" aria-hidden="true">BẠN</span>
        <div className="bubble-body">
          {text}
        </div>
      </div>
    );
  }

  const body = msg.body as ChatResponse | { kind: "text"; text: string };
  if (body.kind === "text") {
    const t = (body as { kind: "text"; text: string }).text;
    if (msg.pending) {
      // Pending state đã được render từ ChatPanel (typing bubble riêng).
      return null;
    }
    return (
      <div className="bubble bubble-assistant">
        <span className="bubble-avatar" aria-hidden="true">VL</span>
        <div className="bubble-body">
          {t}
        </div>
      </div>
    );
  }

  const resp = body as ChatResponse;
  return (
    <div className="bubble bubble-assistant">
      <span className="bubble-avatar" aria-hidden="true">VL</span>
      <article className="bubble-body bubble-article">
        {resp.kind === "outline" && <OutlineView payload={resp.payload as any} />}
        {resp.kind === "part" && <PartView payload={resp.payload as PartSummary} />}
        {resp.kind === "recap" && <RecapView payload={resp.payload as RecapSummary} stats={resp.stats} />}
        {resp.kind === "answer" && <AnswerView payload={resp.payload as AnswerPayload} />}
        {resp.stats && <StatsFooter stats={resp.stats} />}
      </article>
    </div>
  );
}

function OutlineView({ payload }: { payload: { id: string; parts: any[] } }) {
  return (
    <>
      <h3 style={{ marginBottom: "var(--space-3)" }}>
        Buổi {payload.id} có {payload.parts.length} phần
      </h3>
      <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {payload.parts.map((p: any) => (
          <li key={p.idx} style={{ borderTop: "var(--rule)", padding: "var(--space-2) 0" }}>
            <strong>Phần {p.idx}</strong> · {p.title}
            <div style={{ fontSize: "var(--text-micro)", color: "var(--color-muted)" }}>
              {p.n_segments} đoạn · ~{p.n_chars.toLocaleString()} ký tự
              {p.activity_heavy && " · chủ yếu hoạt động lớp"}
            </div>
          </li>
        ))}
      </ul>
      <p style={{ marginTop: "var(--space-3)", fontSize: "var(--text-micro)", color: "var(--color-muted)" }}>
        Gõ “tóm phần 2” để tóm một phần · “tóm cả buổi” để gộp sổ tay.
      </p>
    </>
  );
}

function PartView({ payload }: { payload: PartSummary }) {
  if (payload.skipped) {
    return (
      <>
        <h3 style={{ marginBottom: "var(--space-2)" }}>
          Phần {payload.part.idx} · {payload.part.title}
        </h3>
        <p style={{ color: "var(--color-warning)", fontSize: "var(--text-small)" }}>
          Phần này mình không tóm. {payload.reason}
        </p>
      </>
    );
  }
  return (
    <>
      <header style={{ marginBottom: "var(--space-3)" }}>
        <span className="eyebrow">Phần {payload.part.idx}</span>
        <h3>{payload.part.title}</h3>
      </header>
      {payload.abstract && (
        <p
          style={{
            background: "var(--color-crimson-soft)",
            borderLeft: "3px solid var(--color-crimson)",
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--text-small)",
            marginBottom: "var(--space-4)",
          }}
        >
          {payload.abstract}
        </p>
      )}
      <ol style={{ paddingLeft: "1.25rem", margin: 0 }}>
        {payload.key_points.map((kp, i) => (
          <li key={i} style={{ marginBottom: "var(--space-3)" }}>
            <KeyPointLine kp={kp} />
          </li>
        ))}
      </ol>
      {payload.gaps.length > 0 && (
        <details style={{ marginTop: "var(--space-4)" }}>
          <summary style={{ cursor: "pointer", fontSize: "var(--text-micro)", color: "var(--color-warning)" }}>
            ⚠ {payload.gaps.length} chỗ bản ghi thiếu
          </summary>
          <ul style={{ fontSize: "var(--text-micro)", color: "var(--color-muted)", marginTop: "var(--space-2)" }}>
            {payload.gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

function RecapView({ payload }: { payload: RecapSummary; stats: ChatResponse["stats"] }) {
  return (
    <>
      <header style={{ marginBottom: "var(--space-3)" }}>
        <span className="eyebrow">Sổ tay buổi {payload.session.id}</span>
        <h2 style={{ fontSize: "var(--text-h2)", marginTop: "var(--space-2)" }}>
          {payload.session.title}
        </h2>
        <p style={{ fontSize: "var(--text-micro)", color: "var(--color-muted)" }}>
          {payload.session.n_sections} mục · {payload.session.n_segments} đoạn
        </p>
      </header>
      {payload.tldr && (
        <p
          style={{
            background: "var(--color-crimson-soft)",
            borderLeft: "3px solid var(--color-crimson)",
            padding: "var(--space-3) var(--space-4)",
            borderRadius: "var(--radius-sm)",
            fontSize: "var(--text-small)",
            marginBottom: "var(--space-4)",
          }}
        >
          {payload.tldr}
        </p>
      )}
      <h3 style={{ marginBottom: "var(--space-2)" }}>Ý chính</h3>
      <ol style={{ paddingLeft: "1.25rem", margin: 0 }}>
        {payload.key_points.map((kp, i) => (
          <li key={i} style={{ marginBottom: "var(--space-3)" }}>
            <KeyPointLine kp={kp} />
          </li>
        ))}
      </ol>
      {payload.student_points.length > 0 && (
        <>
          <h3 style={{ marginTop: "var(--space-5)", marginBottom: "var(--space-2)" }}>
            Câu hỏi học viên nêu
          </h3>
          <ul style={{ paddingLeft: "1.25rem", margin: 0 }}>
            {payload.student_points.map((kp, i) => (
              <li key={i} style={{ marginBottom: "var(--space-2)" }}>
                <KeyPointLine kp={kp} />
              </li>
            ))}
          </ul>
        </>
      )}
      {payload.gaps.length > 0 && (
        <details style={{ marginTop: "var(--space-4)" }}>
          <summary style={{ cursor: "pointer", fontSize: "var(--text-micro)", color: "var(--color-warning)" }}>
            ⚠ Chỗ bản ghi thiếu
          </summary>
          <ul style={{ fontSize: "var(--text-micro)", color: "var(--color-muted)" }}>
            {payload.gaps.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

function ClaimItem({ claim }: { claim: Claim }) {
  const [open, setOpen] = useState(false);

  if (!claim.quote) return null;

  return (
    <div style={{ marginBottom: "var(--space-3)" }}>
      {claim.claim && (
        <p style={{ margin: 0, marginBottom: 4 }}>{claim.claim}</p>
      )}
      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
        <button
          onClick={() => setOpen((o) => !o)}
          className="cite cite-btn"
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            fontSize: "var(--text-micro)",
            padding: "1px 6px",
          }}
        >
          {claim.cite[0]} {open ? "▲" : "▼"}
        </button>
      </div>
      {open && (
        <blockquote className="q" style={{ marginTop: "var(--space-2)" }}>
          "{claim.quote}"
        </blockquote>
      )}
    </div>
  );
}

function AnswerView({ payload }: { payload: AnswerPayload }) {
  if (!payload.claims || payload.claims.length === 0) {
    return (
      <p style={{ color: "var(--color-muted)", fontSize: "var(--text-small)" }}>
        {payload.note || "(tra-cứu không có kết quả)"}
      </p>
    );
  }
  return (
    <>
      {payload.claims.map((c, i) => (
        <ClaimItem key={i} claim={c} />
      ))}
      {payload.note && (
        <p style={{ fontSize: "var(--text-micro)", color: "var(--color-muted)", marginTop: "var(--space-2)" }}>
          {payload.note}
        </p>
      )}
    </>
  );
}

function KeyPointLine({ kp }: { kp: KeyPoint }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  function copy() {
    if (!kp.quote) return;
    navigator.clipboard.writeText(kp.quote).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1200);
    });
  }

  return (
    <span style={{ display: "block" }}>
      <span>
        {kp.claim ?? <em style={{ color: "var(--color-muted)" }}>(ý tóm tắt do AI sinh sẽ nằm ở đây)</em>}{" "}
        {kp.cite.map((c, i) => (
          <span key={i} className="cite" style={{ marginRight: 4 }}>{c}</span>
        ))}
        {kp.has_student_speech && (
          <span style={{ fontSize: "var(--text-micro)", color: "var(--color-muted)", marginLeft: 6 }}>
            · một học viên nêu
          </span>
        )}
      </span>
      {kp.quote && (
        <button
          onClick={() => setOpen((o) => !o)}
          className="btn"
          style={{
            marginTop: 4,
            fontSize: "var(--text-micro)",
            padding: "2px 8px",
            background: "transparent",
            border: "none",
            color: "var(--color-navy-soft)",
          }}
        >
          {open ? "Ẩn nguyên văn" : `Nguyên văn · ${kp.cite[0]}`}
        </button>
      )}
      {open && kp.quote && (
        <div style={{ marginTop: 4 }}>
          <blockquote className="q">"{kp.quote}"</blockquote>
          <button
            onClick={copy}
            className={`btn ${copied ? "is-success pulse-once" : ""}`}
            style={{ fontSize: "var(--text-micro)", padding: "2px 8px" }}
          >
            {copied ? "✓ Đã sao chép" : "Sao chép"}
          </button>
        </div>
      )}
    </span>
  );
}

function StatsFooter({ stats }: { stats: NonNullable<ChatResponse["stats"]> }) {
  if (!stats) return null;
  const bits: string[] = [];
  if (stats.llm_calls) bits.push(`🔴 gọi LLM ${stats.llm_calls} lần`);
  if (stats.cache_hits) bits.push(`⚡ cache ${stats.cache_hits} lần`);
  if (stats.seconds) bits.push(`${stats.seconds.toFixed(1)}s`);
  return (
    <footer style={{ marginTop: "var(--space-3)", paddingTop: "var(--space-2)", borderTop: "var(--rule)", fontSize: "var(--text-micro)", color: "var(--color-muted)" }}>
      {bits.length > 0 && <div>{bits.join(" · ")}</div>}
      {stats.router && <div>🧭 router: {stats.router}</div>}
      {stats.outline && <div>🕸 {stats.outline}</div>}
      {stats.warnings.slice(0, 3).map((w, i) => (
        <div key={i}>⚠ {w}</div>
      ))}
    </footer>
  );
}
