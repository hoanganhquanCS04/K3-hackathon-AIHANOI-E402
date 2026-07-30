import { useEffect, useState } from "react";
import { api } from "../lib/api";

// Sidebar "Chế độ chạy" — pattern DevTools:
// • CSS file (sidebar.css) chứa toàn bộ visual
// • Component chỉ compose layout + state
// • Geometry derive từ --sidebar-w (set bởi SessionPage shell)
export function SidebarStatus({
  nDone,
  total,
  lookupCount,
  state,
  onToggle,
}: {
  nDone: number;
  total: number;
  lookupCount?: number;
  state: "open" | "closed";
  onToggle: (next: "open" | "closed") => void;
}) {
  const [label, setLabel] = useState<string>("");
  const [kgOk, setKgOk] = useState<boolean>(false);
  const [force, setForce] = useState<boolean>(false);

  useEffect(() => {
    api.backend().then((b) => {
      setLabel(b.label);
      setKgOk(b.kg.ok);
    }).catch(() => {});
  }, []);

  function toggleForce(next: boolean) {
    setForce(next);
    api.setForce(next).catch(() => setForce(!next));
  }

  const lookupUsed = lookupCount ?? 0;
  const lookupReady = lookupUsed > 0 || kgOk;

  return (
    <aside className={`sbar${state === "closed" ? " is-rail" : ""}`} aria-label="Chế độ chạy">
      <header className="sbar-header">
        <div className="sbar-logo">
          <span className="sbar-logo-mark" aria-hidden="true">⚙</span>
          <span className="sbar-logo-text">
            <span className="sbar-logo-eyebrow">Backend</span>
            <span className="sbar-logo-name">Chế độ chạy</span>
          </span>
        </div>

        <button
          className="sbar-fold"
          data-state={state}
          onClick={() => onToggle(state === "open" ? "closed" : "open")}
          aria-label={state === "open" ? "Thu sidebar (Ctrl+B)" : "Mở sidebar (Ctrl+B)"}
          title={state === "open" ? "Thu lại (Ctrl+B)" : "Mở ra (Ctrl+B)"}
          data-tip={state === "open" ? "Thu sidebar" : "Mở sidebar"}
        >
          <svg viewBox="0 0 16 16" width="12" height="12" aria-hidden="true">
            <path d="M6 4l4 4-4 4" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </header>

      <div className="sbar-body">
        {/* Routing pipeline */}
        <section className="sbar-section">
          <span className="sbar-section-head">Pipeline</span>
          <p className="sbar-mono">{label || "đang tải…"}</p>
          <div className="sbar-pipeline">
            <span className="pipe-step is-active" title="Intent router">
              <span className="pipe-step-dot" />router
            </span>
            <span className="pipe-step is-active" title="Loader">
              <span className="pipe-step-dot" />loader
            </span>
            <span className={`pipe-step${kgOk ? " is-active" : ""}`} title="Knowledge Graph">
              <span className="pipe-step-dot" />KG
            </span>
          </div>
        </section>

        <hr className="sbar-rule" />

        {/* Mode chips */}
        <section className="sbar-section">
          <span className="sbar-section-head">Luồng</span>
          <ul className="sbar-chips">
            <li>
              <div className="chip chip-ok">
                <span className="chip-glyph" aria-hidden="true">✓</span>
                <div className="chip-text">
                  <span className="chip-label">Tóm tắt</span>
                  <span className="chip-state">
                    thật
                    {nDone > 0 && <span className="chip-detail"> · {nDone}/{total} phần</span>}
                  </span>
                </div>
              </div>
            </li>
            <li>
              {lookupReady ? (
                <div className="chip chip-ok">
                  <span className="chip-glyph" aria-hidden="true">✓</span>
                  <div className="chip-text">
                    <span className="chip-label">Tra cứu</span>
                    <span className="chip-state">
                      thật
                      {lookupUsed > 0 && <span className="chip-detail"> · {lookupUsed} lượt</span>}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="chip chip-pending">
                  <span className="chip-glyph" aria-hidden="true">⋯</span>
                  <div className="chip-text">
                    <span className="chip-label">Tra cứu</span>
                    <span className="chip-state">chưa hỏi</span>
                  </div>
                </div>
              )}
            </li>
          </ul>
        </section>

        <hr className="sbar-rule" />

        {/* Force cache toggle */}
        <section className="sbar-section">
          <label className="sbar-toggle">
            <input
              type="checkbox"
              checked={force}
              onChange={(e) => toggleForce(e.target.checked)}
            />
            <span className="sbar-toggle-track" aria-hidden="true">
              <span className="sbar-toggle-thumb" />
            </span>
            <span className="sbar-toggle-label">
              <span>Bỏ qua cache</span>
              <span className="sbar-toggle-hint">
                Mỗi lần tóm gọi LLM mới — dùng để tự kiểm chứng là AI chạy thật.
              </span>
            </span>
          </label>
        </section>

        {/* Footer mini stats */}
        <footer className="sbar-footer">
          <span className="sbar-footer-k">
            {nDone}<span className="sbar-footer-sep">/{total}</span>
          </span>
          <span className="sbar-footer-label">
            phần đã tóm<br />trong buổi này
          </span>
        </footer>
      </div>
    </aside>
  );
}
