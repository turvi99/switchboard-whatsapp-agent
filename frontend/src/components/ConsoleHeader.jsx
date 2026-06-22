import { Megaphone, Users, AlertTriangle, CheckCircle2, MessagesSquare } from "lucide-react";

function StatChip({ icon: Icon, label, value, tone = "muted" }) {
  const toneClasses = {
    muted: "text-muted",
    signal: "text-signal",
    coral: "text-coral",
    amber: "text-amber",
  };
  return (
    <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-surface-raised border border-border-soft">
      <Icon size={12} className={toneClasses[tone]} />
      <span className="font-mono text-[12px] text-paper tabular-nums">{value ?? "—"}</span>
      <span className="text-[10px] text-faint uppercase tracking-wide hidden lg:inline">{label}</span>
    </div>
  );
}

export default function ConsoleHeader({ tenant, stats, connected, onOpenBroadcast }) {
  return (
    <div className="h-14 shrink-0 border-b border-border bg-surface flex items-center justify-between px-4 gap-4">
      <div className="flex items-center gap-3 shrink-0">
        <div className="w-8 h-8 rounded-md bg-ink border border-border flex items-center justify-center relative">
          <span className="w-2.5 h-2.5 rounded-full bg-signal" />
          <span
            className={`absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full border-2 border-surface ${
              connected ? "bg-signal animate-pulse-dot" : "bg-coral"
            }`}
            title={connected ? "Live feed connected" : "Reconnecting…"}
          />
        </div>
        <div className="leading-tight hidden sm:block">
          <p className="font-display font-semibold text-[14px] text-paper tracking-tight">Switchboard</p>
          <p className="text-[10px] text-faint font-mono uppercase tracking-wide">Agent console</p>
        </div>
      </div>

      <div className="flex-1 min-w-0 flex items-center justify-center gap-2 overflow-x-auto scrollbar-none">
        {tenant && (
          <>
            <StatChip icon={Users} label="active" value={stats?.active_sessions} tone="signal" />
            <StatChip icon={AlertTriangle} label="needs human" value={stats?.needs_human} tone="coral" />
            <StatChip icon={CheckCircle2} label="resolved today" value={stats?.resolved_today} tone="muted" />
            <StatChip icon={MessagesSquare} label="messages" value={stats?.total_messages} tone="amber" />
          </>
        )}
      </div>

      <button
        onClick={onOpenBroadcast}
        disabled={!tenant}
        className="shrink-0 flex items-center gap-1.5 text-[12px] font-medium px-3 py-1.5 rounded-md bg-signal text-ink hover:opacity-90 transition-opacity disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <Megaphone size={13} />
        Broadcast
      </button>
    </div>
  );
}
