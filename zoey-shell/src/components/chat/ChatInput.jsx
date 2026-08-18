import { useState, useRef, useCallback } from "react";
import { ArrowUp } from "lucide-react";
import { useZoey } from "../../store/ZoeyProvider";

export default function ChatInput() {
  const { sendMessage, assistantState } = useZoey();
  const [value, setValue] = useState("");
  const taRef = useRef(null);

  const resize = useCallback(() => {
    const el = taRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, []);

  const submit = () => {
    if (!value.trim()) return;
    sendMessage(value);
    setValue("");
    requestAnimationFrame(resize);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const busy = assistantState === "thinking" || assistantState === "executing";

  return (
    <div className="px-6 pb-5 pt-2">
      <div className="mx-auto max-w-[720px] rounded-xl border border-[var(--color-border)] bg-[var(--color-surface-raised)] focus-within:border-[var(--color-text-tertiary)] transition-colors">
        <textarea
          ref={taRef}
          rows={1}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            resize();
          }}
          onKeyDown={onKeyDown}
          placeholder={busy ? "Zoey is working…" : "Ask Zoey anything"}
          className="w-full resize-none bg-transparent px-4 pt-3 pb-2 text-[14px] leading-relaxed text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] outline-none"
        />
        <div className="flex items-center justify-between px-3 pb-2.5">
          <span className="text-[11px] text-[var(--color-text-tertiary)]">Enter to send · Shift+Enter for new line</span>
          <button
            onClick={submit}
            disabled={!value.trim()}
            className="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--color-accent)] text-[#0a0b0d] disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-90 active:scale-95 transition"
          >
            <ArrowUp size={14} strokeWidth={2.6} />
          </button>
        </div>
      </div>
    </div>
  );
}
