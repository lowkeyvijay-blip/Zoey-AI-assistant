const META = {
  idle: { label: "Idle", color: "#62676f" },
  listening: { label: "Listening", color: "#8fa3ff" },
  thinking: { label: "Thinking", color: "#c9b3ff" },
  executing: { label: "Executing", color: "#d9a15b" },
  completed: { label: "Completed", color: "#6fcf97" },
  failed: { label: "Failed", color: "#e2685f" },
  pending: { label: "Pending", color: "#62676f" },
  running: { label: "Running", color: "#d9a15b" },
  blocked: { label: "Blocked", color: "#9aa0ab" },
  cancelled: { label: "Cancelled", color: "#9aa0ab" },
};

export default function StatusPill({ state, size = "sm" }) {
  const meta = META[state] ?? META.idle;
  const pulsing = state === "thinking" || state === "executing" || state === "running" || state === "listening";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border border-[var(--color-border)] bg-[var(--color-surface-raised)] ${
        size === "sm" ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-[12px]"
      } text-[var(--color-text-secondary)]`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {pulsing && (
          <span
            className="absolute inline-flex h-full w-full rounded-full animate-ping opacity-60"
            style={{ background: meta.color }}
          />
        )}
        <span className="relative inline-flex rounded-full h-1.5 w-1.5" style={{ background: meta.color }} />
      </span>
      {meta.label}
    </span>
  );
}
