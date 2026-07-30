import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useState,
  useRef,
  FormEvent,
} from "react";
import {
  api,
  ChatResponse,
  SessionMeta,
  PartSummary,
} from "../lib/api";
import { MessageView } from "./MessageView";

interface ChatMsg {
  id: number;
  role: "user" | "assistant";
  body: ChatResponse | { kind: "text"; text: string };
  pending?: boolean;
}

export interface ChatHandle {
  send: (q: string) => void;
}

export const ChatPanel = forwardRef<ChatHandle, {
  session: SessionMeta;
  slidePart: number;
  onSlideJump: (i: number) => void;
  onMarkDone: (i: number) => void;
  onLookupCount?: (n: number) => void;
}>(function ChatPanel({ session, onMarkDone, onLookupCount }, ref) {
  const [msgs, setMsgs] = useState<ChatMsg[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [lookupCount, setLookupCount] = useState(0);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    onLookupCount?.(lookupCount);
  }, [lookupCount, onLookupCount]);

  // Auto-scroll xuống cuối khi có tin mới
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    }
  }, [msgs.length, pending]);

  // Auto-grow textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
      inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 140) + "px";
    }
  }, [input]);

  function send(q: string) {
    const text = q.trim();
    if (!text) return;
    const userMsg: ChatMsg = { id: Date.now(), role: "user", body: { kind: "text", text } };
    const tempId = userMsg.id + 1;
    setMsgs((m) => [...m, userMsg, { id: tempId, role: "assistant", body: { kind: "text", text: "…" }, pending: true }]);
    setInput("");
    setPending(true);

    api
      .chat(session.id, text)
      .then((resp) => {
        setMsgs((m) => m.map((x) => (x.id === tempId ? { ...x, body: resp, pending: false } : x)));
        if (resp.kind === "part") {
          const p = resp.payload as PartSummary;
          onMarkDone(p.part.idx);
        }
        if (resp.kind === "answer") {
          setLookupCount((n) => n + 1);
        }
      })
      .catch((e) => {
        setMsgs((m) =>
          m.map((x) =>
            x.id === tempId
              ? { ...x, body: { kind: "text", text: `Lỗi: ${String(e)}` }, pending: false }
              : x
          )
        );
      })
      .finally(() => setPending(false));
  }

  useImperativeHandle(ref, () => ({ send }), [session.id]);

  function submit(e: FormEvent) {
    e.preventDefault();
    send(input);
  }

  const nDone = msgs.filter((m) => m.role === "assistant" && (m.body as ChatResponse).kind === "part").length;

  return (
    <section className="chat" aria-label="Hội thoại với trợ lý">
      {/* Header — logo, title, meta, actions */}
      <header className="chat-header">
        <div className="chat-header-text">
          <span className="chat-avatar-main" aria-hidden="true">VL</span>
          <div className="chat-header-titles">
            <span className="chat-eyebrow">Trợ lý buổi học</span>
            <h3 className="chat-title">Hỏi gì cũng được</h3>
            <span className="chat-meta">
              {session.parts.length} phần{nDone > 0 && ` · đã tóm ${nDone}`}
            </span>
          </div>
        </div>
        <div className="chat-header-actions">
          <button
            type="button"
            className="chat-icon-btn"
            title="Cuộn xuống cuối"
            onClick={() => listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" })}
          >
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <path d="M8 2v9m0 0l-3-3m3 3l3-3M3 14h10" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
          <button
            type="button"
            className="chat-icon-btn"
            title="Xoá cuộc trò chuyện"
            onClick={() => setMsgs([])}
            disabled={msgs.length === 0}
          >
            <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
              <path d="M3 4h10M5 4V2.5A.5.5 0 015.5 2h5a.5.5 0 01.5.5V4M4 4l.5 9a.5.5 0 00.5.5h6a.5.5 0 00.5-.5L12 4" stroke="currentColor" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </header>

      {/* List */}
      <div className="chat-list" ref={listRef} role="log" aria-live="polite">
        {msgs.length === 0 ? (
          <EmptyState />
        ) : (
          msgs.map((m) => <MessageView key={m.id} msg={m} />)
        )}

        {pending && (
          <div className="bubble bubble-assistant bubble-pending">
            <span className="bubble-avatar" aria-hidden="true">VL</span>
            <div className="bubble-body">
              <span className="typing">
                <span /><span /><span />
              </span>
              <span className="bubble-meta">đang soạn…</span>
            </div>
          </div>
        )}
      </div>

      {/* Quick suggestions */}
      <SuggestionStrip onPick={send} />

      {/* Composer dock */}
      <form className="chat-composer" onSubmit={submit}>
        <div className="chat-composer-wrap">
          <label htmlFor="chat-input" style={{ position: "absolute", left: -9999 }}>Nhập câu hỏi</label>
          <textarea
            id="chat-input"
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(e);
              }
            }}
            placeholder="Hỏi về buổi này — ví dụ: tóm tắt phần I"
            disabled={pending}
            className="chat-composer-input"
            rows={1}
          />
          <span className="chat-composer-hint">
            <kbd>Enter</kbd> gửi · <kbd>Shift</kbd>+<kbd>Enter</kbd> xuống dòng
          </span>
        </div>
        <button
          type="submit"
          className="chat-composer-send"
          disabled={pending || !input.trim()}
          aria-label="Gửi"
          title="Gửi (Enter)"
        >
          {pending ? (
            <span className="spinner" />
          ) : (
            <svg viewBox="0 0 16 16" width="16" height="16" aria-hidden="true">
              <path d="M2 8l12-6-4 14-3-6-5-2z" stroke="currentColor" strokeWidth="1.6" fill="currentColor" strokeLinejoin="round" />
            </svg>
          )}
        </button>
      </form>
    </section>
  );
});

function SuggestionStrip({ onPick }: { onPick: (q: string) => void }) {
  const suggestions = [
    "Buổi này có mấy phần?",
    "Tóm phần 1",
    "Tóm cả buổi",
    "Tóm phần khó nhất",
    "Sinh viên nói gì?",
  ];
  return (
    <div className="sugg-strip" aria-label="Gợi ý">
      {suggestions.map((s) => (
        <button key={s} onClick={() => onPick(s)} className="sugg-pill" type="button">
          <span className="sugg-glyph" aria-hidden="true">→</span>
          {s}
        </button>
      ))}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="chat-empty">
      <span className="chat-empty-glyph" aria-hidden="true">✦</span>
      <h4>Bắt đầu từ một câu hỏi</h4>
      <p>
        Trợ lý đọc thẳng từ bản ghi buổi — cứ hỏi tiếng Việt hay tiếng Anh đều được.
        Mỗi ý trong câu trả lời đều có trích dẫn về transcript.
      </p>
    </div>
  );
}
