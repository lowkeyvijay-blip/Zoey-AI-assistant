import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Calendar as CalendarIcon, Inbox } from "lucide-react";
import { api } from "../../lib/api";

export default function CalendarPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.events(20);
      setData(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 h-12 border-b border-[var(--color-border-soft)]">
        <div className="flex items-center gap-2 text-[13px] font-medium text-[var(--color-text-primary)]">
          <CalendarIcon size={14} strokeWidth={1.8} />
          Upcoming events
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-raised)] transition-colors"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-1.5">
        {error && (
          <p className="text-[12px] text-[var(--color-rose)]">{error}</p>
        )}
        {loading && !data && (
          <p className="text-[12px] text-[var(--color-text-tertiary)]">Loading…</p>
        )}
        {!loading && data && data.length === 0 && (
          <div className="flex flex-col items-center gap-1 py-8 text-[var(--color-text-tertiary)]">
            <Inbox size={18} strokeWidth={1.6} />
            <p className="text-[12px]">No upcoming events.</p>
          </div>
        )}
        {data?.map((event) => (
          <div
            key={event.id}
            className="rounded-lg border border-[var(--color-border-soft)] bg-[var(--color-surface-raised)] px-3 py-2"
          >
            <p className="text-[13px] text-[var(--color-text-primary)] leading-snug">{event.title}</p>
            <p className="text-[11px] text-[var(--color-text-tertiary)] mt-0.5">
              {event.start_at}
              {event.location ? ` · ${event.location}` : ""}
            </p>
            {event.notes && (
              <p className="text-[11px] text-[var(--color-text-secondary)] mt-0.5">{event.notes}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
