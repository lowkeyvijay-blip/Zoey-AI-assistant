import { Square } from "lucide-react";
import StepRow from "./StepRow";
import StatusPill from "../common/StatusPill";
import { useZoey } from "../../store/ZoeyProvider";

const TERMINAL_STATUSES = new Set([
  "completed",
  "failed",
  "cancelled",
  "blocked",
  "no_executable_steps",
]);

const LABEL_BY_STATUS = {
  completed: "Completed",
  failed: "Failed",
  cancelled: "Cancelled",
  blocked: "Blocked",
  no_executable_steps: "Finished",
};

export default function ExecutionCard({ goal, steps, status }) {
  const { cancelExecution } = useZoey();

  const total = steps.length;
  const doneCount = steps.filter((s) => s.status === "completed").length;
  const progress = total > 0 ? Math.round((doneCount / total) * 100) : 0;
  const terminal = TERMINAL_STATUSES.has(status);
  const title = terminal ? LABEL_BY_STATUS[status] || "Finished" : "Executing";

  return (
    <div className="w-full max-w-[560px] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] overflow-hidden animate-rise">
      <div className="flex items-center justify-between px-4 pt-3.5 pb-3 border-b border-[var(--color-border-soft)]">
        <div className="min-w-0">
          <p className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] mb-1">{title}</p>
          <p className="text-[14px] text-[var(--color-text-primary)] leading-snug truncate">{goal}</p>
        </div>
        <StatusPill state={status} />
      </div>

      <div className="px-4 pt-3">
        <div className="h-1 w-full rounded-full bg-[var(--color-border-soft)] overflow-hidden">
          <div
            className="h-full rounded-full bg-[var(--color-accent)] transition-all duration-500 ease-out"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="px-4 py-1 divide-y divide-[var(--color-border-soft)]">
        {steps.length === 0 && (
          <p className="py-3 text-[12px] text-[var(--color-text-tertiary)]">
            {terminal ? "No step details yet." : "Starting…"}
          </p>
        )}
        {steps.map((step) => (
          <StepRow key={step.number} step={step} />
        ))}
      </div>

      {status === "running" && (
        <div className="px-4 py-2.5 border-t border-[var(--color-border-soft)]">
          <button
            onClick={cancelExecution}
            className="flex items-center gap-1.5 text-[12px] text-[var(--color-text-secondary)] hover:text-[var(--color-rose)] transition-colors"
          >
            <Square size={11} strokeWidth={2.4} />
            Stop execution
          </button>
        </div>
      )}
    </div>
  );
}
