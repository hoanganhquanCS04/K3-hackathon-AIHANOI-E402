import { Link } from "react-router-dom";
import { SessionMeta } from "../lib/api";

// Pool map index (1..6) → CSS variable name. Trùng với --image-cover-{1,2,3,7,8,9}.
const POOL: Record<number, string> = {
  1: "var(--image-cover-1)",
  2: "var(--image-cover-2)",
  3: "var(--image-cover-3)",
  4: "var(--image-cover-7)",
  5: "var(--image-cover-8)",
  6: "var(--image-cover-9)",
};

// Editorial session card — chapter-list item.
// Day badge uses monospace numerals (anti-AI-slop signal of editorial press).
// `imageIndex` (1..6) chọn ảnh từ rotation pool — HomePage truyền vào.
export function SessionCard({
  session,
  imageIndex = 1,
  staggerIndex = 0,
}: {
  session: SessionMeta;
  imageIndex?: number;
  staggerIndex?: number;
}) {
  const conf = session.locate_confidence.toLowerCase();
  const isWarn = conf !== "cao";
  const img = POOL[((imageIndex - 1) % 6) + 1] ?? POOL[1];

  return (
    <Link
      to={`/buoi/${session.id}`}
      className="card card-link"
      style={{
        "--i": staggerIndex,
        textDecoration: "none",
        color: "inherit",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
        minWidth: 0,            /* gate 51 */
      } as React.CSSProperties}
    >
      <div
        className="card-thumb"
        aria-hidden="true"
        style={{ "--image-cover": img } as React.CSSProperties}
      />

      <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
        <span
          aria-hidden="true"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--text-micro)",
            letterSpacing: "0.12em",
            color: "var(--color-crimson)",
            fontWeight: 500,
          }}
        >
          BUỔI {session.id}
        </span>
        {isWarn && (
          <span
            style={{
              background: "oklch(95% 0.08 85)",
              color: "oklch(40% 0.12 60)",
              fontSize: "var(--text-micro)",
              padding: "1px 8px",
              borderRadius: 20,
              fontWeight: 600,
            }}
          >
            ⚠ định vị: {conf}
          </span>
        )}
      </div>

      <h3
        style={{
          fontFamily: "var(--font-body)",
          fontSize: "1.4rem",
          color: "var(--color-navy)",
          lineHeight: 1.25,
        }}
      >
        {session.title}
      </h3>

      <p
        style={{
          fontSize: "var(--text-small)",
          color: "var(--color-muted)",
          margin: 0,
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {session.parts.length} phần · {session.n_sections} mục · {session.n_segments} đoạn
        {session.n_unclear > 0 && ` · ${session.n_unclear} đoạn thiếu`}
      </p>
    </Link>
  );
}