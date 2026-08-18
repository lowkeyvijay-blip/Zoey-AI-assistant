import { Check, X, Loader2, Circle, Ban, Clock } from "lucide-react";

const ICON_BY_STATUS = {
  pending: { Icon: Circle, color: "var(--color-text-tertiary)", spin: false },
  running: { Icon: Loader2, color: "var(--color-amber)", spin: true },
  completed: { Icon: Check, color: "var(--color-emerald)", spin: false },
  failed: { Icon: X, color: "var(--color-rose)", spin: false },
  blocked: { Icon: Clock, color: "var(--color-text-tertiary)", spin: false },
  cancelled: { Icon: Ban, color: "var(--color-text-tertiary)", spin: false },
  not_auto: { Icon: Clock, color: "var(--color-text-tertiary)", spin: false },
};

export default function StepRow({ step, compact = false }) {
  const meta = ICON_BY_STATUS[step.status] ?? ICON_BY_STATUS.pending;
  const { Icon } = meta;

  return (
    <div className={`flex items-start gap-3 ${compact ? "py-1.5" : "py-2"}`}>
      <span
        className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full"
        style={{
          background: step.status === "pending" ? "transparent" : `${meta.color}1a`,
          border: `1px solid ${step.status === "pending" ? "var(--color-border)" : meta.color}`,
        }}
      >
        <Icon size={11} strokeWidth={2.4} style={{ color: meta.color }} className={meta.spin ? "animate-spin" : ""} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p
            className={`text-[13px] leading-snug truncate ${
              step.status === "completed" ? "text-[var(--color-text-secondary)]" : "text-[var(--color-text-primary)]"
            }`}
          >
            {step.title}
          </p>
          <span className="text-[11px] text-[var(--color-text-tertiary)] font-mono shrink-0">{step.tool}</span>
        </div>
        {step.status === "failed" && step.result?.error && (
          <p className="text-[11px] text-[var(--color-rose)] mt-0.5">{step.result.error}</p>
        )}
        {step.status === "completed" && !compact && step.result?.summary && (
          <p className="text-[11px] text-[var(--color-text-tertiary)] mt-0.5">{step.result.summary}</p>
        )}
      </div>
    </div>
  );
}
