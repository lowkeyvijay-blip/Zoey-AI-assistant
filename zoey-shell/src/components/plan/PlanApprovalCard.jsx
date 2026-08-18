import { Check, X, GitBranch, Play } from "lucide-react";
import { useZoey } from "../../store/ZoeyProvider";

export default function PlanApprovalCard({ messageId, plan, decision }) {
  const { approvePlan, rejectPlan, executePlan, execStatus } = useZoey();

  if (!plan) return null;

  const running = execStatus === "running";

  return (
    <div className="w-full max-w-[560px] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] overflow-hidden animate-rise">
      <div className="px-4 pt-3.5 pb-3 border-b border-[var(--color-border-soft)]">
        <p className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)] mb-1">
          Proposed plan
        </p>
        <p className="text-[14px] text-[var(--color-text-primary)] leading-snug">{plan.goal}</p>
      </div>

      <ol className="px-4 py-3 flex flex-col gap-2.5">
        {plan.steps.map((step) => (
          <li key={step.number} className="flex items-start gap-2.5">
            <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-[var(--color-border)] text-[10px] text-[var(--color-text-tertiary)]">
              {step.number}
            </span>
            <div className="min-w-0">
              <p className="text-[13px] text-[var(--color-text-primary)] leading-snug">{step.title}</p>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-[11px] text-[var(--color-text-tertiary)] font-mono">{step.tool}</span>
                {step.depends_on?.length > 0 && (
                  <span className="flex items-center gap-1 text-[11px] text-[var(--color-text-tertiary)]">
                    <GitBranch size={10} />
                    after {step.depends_on.join(", ")}
                  </span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>

      {decision === null && (
        <div className="flex items-center gap-2 px-4 py-3 border-t border-[var(--color-border-soft)]">
          <button
            onClick={() => approvePlan(messageId)}
            className="flex-1 flex items-center justify-center gap-1.5 rounded-lg bg-[var(--color-accent)] text-[#0a0b0d] text-[13px] font-medium py-2 hover:opacity-90 active:scale-[0.98] transition"
          >
            <Check size={14} strokeWidth={2.4} />
            Approve
          </button>
          <button
            onClick={() => rejectPlan(messageId)}
            className="flex-1 flex items-center justify-center gap-1.5 rounded-lg border border-[var(--color-border)] text-[var(--color-text-secondary)] text-[13px] py-2 hover:text-[var(--color-text-primary)] hover:border-[var(--color-text-tertiary)] transition"
          >
            <X size={14} strokeWidth={2.4} />
            Reject
          </button>
        </div>
      )}

      {decision === "approved" && (
        <div className="px-4 py-3 border-t border-[var(--color-border-soft)] bg-[var(--color-emerald-soft)]">
          <p className="text-[12px] text-[var(--color-emerald)] mb-2.5">
            Approved — ready to execute.
          </p>
          <button
            onClick={executePlan}
            disabled={running}
            className="flex items-center justify-center gap-1.5 w-full rounded-lg bg-[var(--color-emerald)] text-[#0a0b0d] text-[13px] font-medium py-2 hover:opacity-90 active:scale-[0.98] transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Play size={13} strokeWidth={2.4} />
            {running ? "Executing…" : "Execute plan"}
          </button>
        </div>
      )}

      {decision === "rejected" && (
        <div className="px-4 py-2.5 border-t border-[var(--color-border-soft)] bg-[var(--color-rose-soft)]">
          <p className="text-[12px] text-[var(--color-rose)]">Discarded.</p>
        </div>
      )}
    </div>
  );
}
