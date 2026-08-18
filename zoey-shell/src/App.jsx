import Sidebar from "./components/sidebar/Sidebar";
import MessageList from "./components/chat/MessageList";
import ChatInput from "./components/chat/ChatInput";
import StatusPill from "./components/common/StatusPill";
import TasksPanel from "./components/panels/TasksPanel";
import CalendarPanel from "./components/panels/CalendarPanel";
import FilesPanel from "./components/panels/FilesPanel";
import MemoryPanel from "./components/panels/MemoryPanel";
import NotificationsPanel from "./components/panels/NotificationsPanel";
import { useZoey } from "./store/ZoeyProvider";

const PANELS = {
  tasks: TasksPanel,
  calendar: CalendarPanel,
  files: FilesPanel,
  memory: MemoryPanel,
  notifications: NotificationsPanel,
};

export default function App() {
  const { assistantState, panel } = useZoey();
  const Panel = PANELS[panel.view] ?? null;

  return (
    <div className="flex h-screen w-screen bg-[var(--color-bg)] text-[var(--color-text-primary)] overflow-hidden">
      <Sidebar />
      {Panel && (
        <aside className="w-[300px] shrink-0 h-full border-r border-[var(--color-border-soft)] bg-[var(--color-surface)] animate-rise">
          <Panel />
        </aside>
      )}
      <main className="flex flex-1 flex-col min-w-0">
        <header className="flex h-14 shrink-0 items-center justify-end border-b border-[var(--color-border-soft)] px-6">
          <StatusPill state={assistantState} />
        </header>
        <MessageList />
        <ChatInput />
      </main>
    </div>
  );
}
