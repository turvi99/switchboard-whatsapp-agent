import { Loader2, CheckCircle2, AlertTriangle, Sparkles } from "lucide-react";
import { STATUS_META } from "../lib/format";

const ICONS = {
  WAITING_FOR_BOT: Loader2,
  AGENT_RESPONDING: Sparkles,
  RESOLVED: CheckCircle2,
  NEEDS_HUMAN: AlertTriangle,
};

const COLOR_CLASSES = {
  amber: "bg-amber/10 text-amber border-amber/30",
  signal: "bg-signal/10 text-signal border-signal/30",
  muted: "bg-faint/10 text-muted border-faint/30",
  coral: "bg-coral/10 text-coral border-coral/30",
};

export default function StatusPill({ status, size = "sm" }) {
  const meta = STATUS_META[status] || STATUS_META.RESOLVED;
  const Icon = ICONS[status] || CheckCircle2;
  const spin = status === "WAITING_FOR_BOT";
  const sizeClasses = size === "sm" ? "text-[11px] px-2 py-0.5 gap-1" : "text-xs px-2.5 py-1 gap-1.5";

  return (
    <span
      className={`inline-flex items-center rounded-full border font-mono uppercase tracking-wide whitespace-nowrap ${COLOR_CLASSES[meta.color]} ${sizeClasses}`}
      title={meta.description}
    >
      <Icon size={size === "sm" ? 11 : 13} className={spin ? "animate-spin" : ""} />
      {meta.label}
    </span>
  );
}
