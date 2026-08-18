import { useEffect, useRef } from "react";
import { useZoey } from "../../store/ZoeyProvider";
import PlanApprovalCard from "../plan/PlanApprovalCard";
import ExecutionCard from "../execution/ExecutionCard";

export default function MessageList() {
  const { messages, plan, decision, steps, execStatus, execution } = useZoey();
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, decision, steps]);

  return (
    <div className="flex-1 overflow-y-auto px-6 py-6">
      <div className="mx-auto flex max-w-[720px] flex-col gap-4">
        {messages.map((m) => {
          if (m.type === "text" || m.type === "plan_executed") {
            const isUser = m.role === "user";
            return (
              <div key={m.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                <p
                  className={`max-w-[80%] text-[14px] leading-relaxed rounded-xl px-3.5 py-2.5 ${
                    isUser
                      ? "bg-[var(--color-surface-raised)] text-[var(--color-text-primary)]"
                      : "text-[var(--color-text-secondary)]"
                  }`}
                >
                  {m.content}
                </p>
              </div>
            );
          }

          if (m.type === "error") {
            return (
              <div key={m.id} className="flex justify-start">
                <p className="max-w-[80%] text-[14px] leading-relaxed rounded-xl px-3.5 py-2.5 text-[var(--color-rose)] border border-[var(--color-rose)]/30 bg-[var(--color-rose-soft)]">
                  {m.content}
                </p>
              </div>
            );
          }

          if (m.type === "plan_pending" || m.type === "goal") {
            const messagePlan = m.data && m.data.plan;
            return (
              <PlanApprovalCard
                key={m.id}
                messageId={m.id}
                plan={messagePlan || plan}
                decision={decision}
              />
            );
          }

          return null;
        })}

        {execution && (
          <ExecutionCard goal={execution.goal} steps={steps} status={execStatus} />
        )}

        <div ref={endRef} />
      </div>
    </div>
  );
}
