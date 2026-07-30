import { PartMeta, SessionMeta } from "../lib/api";

// Pool map index (1..6) → CSS variable name. Trùng với --image-cover-{1,2,3,7,8,9}.
const POOL: Record<number, string> = {
  1: "var(--image-cover-1)",
  2: "var(--image-cover-2)",
  3: "var(--image-cover-3)",
  4: "var(--image-cover-7)",
  5: "var(--image-cover-8)",
  6: "var(--image-cover-9)",
};

function pickImage(sessionId: string, partIdx: number): string {
  let h = 0;
  for (let i = 0; i < sessionId.length; i++) h = (h * 31 + sessionId.charCodeAt(i)) >>> 0;
  return POOL[((h + partIdx) % 6) + 1] ?? POOL[1];
}

// Slide placeholder — gradient frame, no fake chrome (gate 47).
// Real slide image would replace this when codebase/slides/{sid}-{idx}.png exists.
// Background campus image rotates theo (sessionId, partIdx) → mỗi slide ảnh khác nhau.
export function SlideFrame({
  session,
  part,
}: {
  session: SessionMeta;
  part: PartMeta;
}) {
  const img = pickImage(session.id, part.idx);

  return (
    <figure
      className="fade-up slide-cover"
      style={{
        "--image-cover": img,
        aspectRatio: "16 / 9",
        borderRadius: "var(--radius-lg)",
        padding: "var(--space-7) var(--space-7)",
        background: "linear-gradient(152deg, var(--color-navy-soft) 0%, var(--color-navy-deep) 100%)",
        color: "var(--color-paper)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        margin: 0,
        boxShadow: "0 12px 28px color-mix(in oklch, var(--color-navy-deep) 30%, transparent)",
      } as React.CSSProperties}
    >
      <figcaption style={{ fontSize: "var(--text-micro)", letterSpacing: "0.16em", textTransform: "uppercase", color: "color-mix(in oklch, white 65%, transparent)" }}>
        Buổi {session.id} · Phần {part.idx}
      </figcaption>
      <h2 style={{ color: "var(--color-paper)", fontSize: "2.1rem", lineHeight: 1.25 }}>
        {part.title}
      </h2>
      <footer style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", fontSize: "var(--text-micro)", color: "color-mix(in oklch, white 55%, transparent)" }}>
        <span style={{ border: "1px dashed color-mix(in oklch, white 35%, transparent)", borderRadius: 4, padding: "2px 8px", letterSpacing: "0.08em" }}>
          SLIDE MINH HOẠ
        </span>
        <span style={{ fontFamily: "var(--font-mono)" }}>{part.idx} / {session.parts.length}</span>
      </footer>
    </figure>
  );
}