import { useCallback, useEffect, useState } from "react";
import { RefreshCw, FolderOpen, Folder, FileText, Inbox } from "lucide-react";
import { api } from "../../lib/api";

function formatSize(bytes) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

export default function FilesPanel() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [path, setPath] = useState(".");

  const load = useCallback(async (target) => {
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.files(target);
      setData(data);
      setPath(data.path || ".");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(".");
  }, [load]);

  const navigate = (dir) => {
    const base = path === "." ? "" : path;
    const next = dir === ".." ? (base.includes("/") ? base.replace(/\/[^/]*$/, "") : ".") : `${base}/${dir}`;
    load(next);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 h-12 border-b border-[var(--color-border-soft)]">
        <div className="flex items-center gap-2 text-[13px] font-medium text-[var(--color-text-primary)]">
          <FolderOpen size={14} strokeWidth={1.8} />
          Files
        </div>
        <button
          onClick={() => load(path)}
          className="flex items-center gap-1.5 rounded-md px-2 py-1 text-[12px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] hover:bg-[var(--color-surface-raised)] transition-colors"
        >
          <RefreshCw size={12} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      <div className="px-4 pt-3 pb-1">
        <p className="text-[11px] font-mono text-[var(--color-text-tertiary)] truncate">
          /{path === "." ? "" : path}
        </p>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-2 flex flex-col gap-0.5">
        {error && (
          <p className="text-[12px] text-[var(--color-rose)]">{error}</p>
        )}
        {loading && !data && (
          <p className="text-[12px] text-[var(--color-text-tertiary)]">Loading…</p>
        )}
        {!loading && data && data.entries.length === 0 && (
          <div className="flex flex-col items-center gap-1 py-8 text-[var(--color-text-tertiary)]">
            <Inbox size={18} strokeWidth={1.6} />
            <p className="text-[12px]">Empty directory.</p>
          </div>
        )}
        {path !== "." && (
          <button
            onClick={() => navigate("..")}
            className="flex items-center gap-2 rounded-md px-2 py-1.5 text-[12px] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-raised)] transition-colors text-left"
          >
            <Folder size={13} strokeWidth={1.8} />
            ../
          </button>
        )}
        {data?.entries.map((entry) => (
          <button
            key={entry.name}
            onClick={() => entry.type === "directory" && navigate(entry.name)}
            disabled={entry.type !== "directory"}
            className={`flex items-center gap-2 rounded-md px-2 py-1.5 text-left transition-colors ${
              entry.type === "directory"
                ? "text-[var(--color-text-primary)] hover:bg-[var(--color-surface-raised)]"
                : "text-[var(--color-text-secondary)] cursor-default"
            }`}
          >
            {entry.type === "directory" ? (
              <Folder size={13} strokeWidth={1.8} />
            ) : (
              <FileText size={13} strokeWidth={1.8} />
            )}
            <span className="flex-1 min-w-0 text-[12px] truncate">{entry.name}</span>
            {entry.type === "file" && (
              <span className="shrink-0 text-[10px] text-[var(--color-text-tertiary)] font-mono">
                {formatSize(entry.size)}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
