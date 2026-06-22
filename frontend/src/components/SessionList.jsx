import { AlertTriangle } from "lucide-react";
import StatusPill from "./StatusPill";
import { formatPhone, formatRelativeTime, STATUS_META } from "../lib/format";

const FILTERS = [
  { key: null, label: "All" },
  { key: "WAITING_FOR_BOT", label: "Waiting" },
  { key: "NEEDS_HUMAN", label: "Needs human" },
  { key: "RESOLVED", label: "Resolved" },
];

const ROW_BORDER = {
  amber: "border-l-amber",
  signal: "border-l-signal",
  muted: "border-l-faint/40",
  coral: "border-l-coral",
};

export default function SessionList({ sessions, selectedId, onSelect, filter, onFilterChange, loading }) {
  return (
    <div className="w-[320px] shrink-0 border-r border-border flex flex-col bg-surface">
      <div className="px-4 pt-4 pb-3 border-b border-border">
        <h3 className="font-display font-semibold text-[13px] text-paper mb-2.5">Live sessions</h3>
        <div className="flex gap-1 flex-wrap">
          {FILTERS.map((f) => (
            <button
              key={f.label}
              onClick={() => onFilterChange(f.key)}
              className={[
                "text-[10.5px] font-mono uppercase tracking-wide px-2 py-1 rounded transition-colors",
                filter === f.key
                  ? "bg-signal/15 text-signal border border-signal/30"
                  : "text-faint border border-transparent hover:text-muted hover:bg-surface-hover",
              ].join(" ")}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {loading && <p className="text-center text-xs text-faint mt-6">Loading sessions…</p>}
        {!loading && sessions.length === 0 && (
          <p className="text-center text-xs text-faint mt-6 px-4">No conversations on this line yet.</p>
        )}
        {sessions.map((s) => {
          const meta = STATUS_META[s.status] || STATUS_META.RESOLVED;
          const isSelected = s.session_id === selectedId;
          return (
            <button
              key={s.session_id}
              onClick={() => onSelect(s)}
              className={[
                "w-full text-left px-4 py-3 border-l-2 border-b border-b-border-soft transition-colors",
                ROW_BORDER[meta.color],
                isSelected ? "bg-surface-hover" : "hover:bg-surface-hover/60",
                s.status === "NEEDS_HUMAN" ? "bg-coral/[0.04]" : "",
              ].join(" ")}
            >
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-mono text-[12.5px] text-paper truncate">
                  {formatPhone(s.customer_phone)}
                </span>
                <span className="text-[10px] text-faint font-mono shrink-0">
                  {formatRelativeTime(s.updated_at)}
                </span>
              </div>
              <p className="text-[12px] text-muted truncate mb-1.5">
                {s.last_message_preview || "No messages yet"}
              </p>
              <div className="flex items-center gap-1.5">
                <StatusPill status={s.status} />
                {s.status === "NEEDS_HUMAN" && <AlertTriangle size={11} className="text-coral" />}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
