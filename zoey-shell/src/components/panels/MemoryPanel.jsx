import { useCallback, useEffect, useState } from "react";
import { RefreshCw, BrainCircuit, Inbox } from "lucide-react";
import { api } from "../../lib/api";

const TYPE_COLORS = {
  note: "var(--color-text-tertiary)",
  event: "var(--color-amber)",
  task: "var(--color-emerald)",
  command: "var(--color-accent)",
  fact: "var(--color-blue)",
};

export default function MemoryPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [type, setType] = useState("");

  const load = useCallback(async (filter) => {
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.memories(filter, 20);
      setData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load("");
  }, [load]);

  const changeType = (next) => {
    setType(next);
    load(next);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 h-12 border-b border-[var(--color-border-soft)]">
        <div className="flex items-center gap-2 text-[13px] font-medium text-[var(--color-text-primary)]">
          <BrainCircuit size={14} strokeWidth={1.8} />
          Memory
        </div>
        <button
          onClick={() => load(type)}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-raised)] transition-colors"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      <div className="px-4 pt-2.5 pb-1 flex items-center gap-1.5">
        {["", "note", "event", "task", "command", "fact"].map((t) => (
          <button
            key={t || "all"}
            onClick={() => changeType(t)}
            className={`rounded-full px-2.5 py-1 text-[11px] transition-colors ${
              type === t
                ? "bg-[var(--color-accent-soft)] text-[var(--color-text-primary)]"
                : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)]"
            }`}
          >
            {t || "all"}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-2 flex flex-col gap-1.5">
        {error && (
          <p className="text-[12px] text-[var(--color-rose)]">{error}</p>
        )}
        {loading && !data && (
          <p className="text-[12px] text-[var(--color-text-tertiary)]">Loading…</p>
        )}
        {!loading && data && data.length === 0 && (
          <div className="flex flex-col items-center gap-1 py-8 text-[var(--color-text-tertiary)]">
            <Inbox size={18} strokeWidth={1.6} />
            <p className="text-[12px]">No memories saved.</p>
          </div>
        )}
        {data?.map((memory) => (
          <div
            key={memory.id}
            className="rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-surface-raised)] px-3 py-2"
          >
            <p className="text-[13px] text-[var(--color-text-primary)] leading-snug">{memory.content}</p>
            <div className="flex items-center gap-2 mt-1">
              <span
                className="text-[10px] px-1.5 py-0.5 rounded-full border"
                style={{
                  color: TYPE_COLORS[memory.memory_type] || "var(--color-text-tertiary)",
                  borderColor: TYPE_COLORS[memory.memory_type] || "var(--color-border)",
                }}
              >
                {memory.memory_type}
              </span>
              <span className="text-[11px] text-[var(--color-text-tertiary)]">{memory.created_at}</span>
              {memory.importance != null && memory.importance > 1 && (
                <span className="text-[11px] text-[var(--color-amber)]">★ {memory.importance}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
