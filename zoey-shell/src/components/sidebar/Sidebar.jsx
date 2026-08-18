import {
  MessageSquare,
  CheckSquare,
  Calendar,
  FolderOpen,
  BrainCircuit,
  Settings,
  Bell,
  Plus,
} from "lucide-react";
import { useZoey } from "../../store/ZoeyProvider";
import ZoeyAvatar from "../avatar/ZoeyAvatar";

const NAV_ITEMS = [
  { id: "tasks", label: "Tasks", icon: CheckSquare },
  { id: "calendar", label: "Calendar", icon: Calendar },
  { id: "files", label: "Files", icon: FolderOpen },
  { id: "memory", label: "Memory", icon: BrainCircuit },
  { id: "notifications", label: "Notifications", icon: Bell },
];

export default function Sidebar() {
  const { conversations, panel, openPanel, assistantState, newConversation } = useZoey();

  return (
    <aside className="w-[248px] shrink-0 h-full flex flex-col border-r border-[var(--color-border-soft)] bg-[var(--color-surface)]">
      <div className="flex items-center gap-2.5 px-4 h-14 border-b border-[var(--color-border-soft)]">
        <ZoeyAvatar state={assistantState} size={26} />
        <span className="text-[13px] font-medium tracking-wide text-[var(--color-text-primary)]">
          Zoey
        </span>
      </div>

      <div className="px-3 pt-3">
        <button
          onClick={newConversation}
          className="w-full flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] text-[var(--color-text-secondary)] border border-[var(--color-border-soft)] hover:border-[var(--color-border)] hover:text-[var(--color-text-primary)] transition-colors"
        >
          <Plus size={14} strokeWidth={2} />
          New conversation
        </button>
      </div>

      <nav className="px-3 pt-4 flex flex-col gap-0.5">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = panel.view === item.id;
          return (
            <button
              key={item.id}
              onClick={() => openPanel(item.id)}
              className={`flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] transition-colors ${
                active
                  ? "bg-[var(--color-accent-soft)] text-[var(--color-text-primary)]"
                  : "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-text-primary)]"
              }`}
            >
              <Icon size={15} strokeWidth={1.8} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="mt-5 px-4 pb-1">
        <p className="text-[11px] uppercase tracking-wider text-[var(--color-text-tertiary)]">
          Conversations
        </p>
      </div>
      <div className="flex-1 overflow-y-auto px-3 pb-3 flex flex-col gap-0.5">
        {conversations.map((c) => (
          <button
            key={c.id}
            className={`group flex items-start gap-2.5 rounded-lg px-3 py-2 text-left transition-colors ${
              c.active
                ? "bg-[var(--color-surface-raised)]"
                : "hover:bg-[var(--color-surface-raised)]"
            }`}
          >
            <MessageSquare size={14} className="mt-0.5 text-[var(--color-text-tertiary)]" strokeWidth={1.8} />
            <span className="flex-1 min-w-0">
              <span className="block text-[13px] text-[var(--color-text-primary)] truncate">
                {c.title}
              </span>
              <span className="block text-[11px] text-[var(--color-text-tertiary)]">{c.updated}</span>
            </span>
          </button>
        ))}
      </div>

      <div className="px-3 py-3 border-t border-[var(--color-border-soft)]">
        <button className="w-full flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-text-primary)] transition-colors">
          <Settings size={15} strokeWidth={1.8} />
          Settings
        </button>
      </div>
    </aside>
  );
}
