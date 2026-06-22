// Formatting helpers shared across the console. Kept dependency-free
// (no date-fns) since the formatting needs here are narrow.

export function formatPhone(phone) {
  if (!phone) return "";
  const digits = phone.replace(/[^\d]/g, "");
  if (digits.length === 11 && digits.startsWith("1")) {
    return `+1 (${digits.slice(1, 4)}) ${digits.slice(4, 7)}-${digits.slice(7)}`;
  }
  if (digits.length === 10) {
    return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
  }
  return `+${digits}`;
}

export function formatRelativeTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.round(diffMs / 1000);
  const diffMin = Math.round(diffSec / 60);
  const diffHr = Math.round(diffMin / 60);
  const diffDay = Math.round(diffHr / 24);

  if (diffSec < 10) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatClockTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString);
  return date.toLocaleTimeString(undefined, {
    hour: "numeric",
    minute: "2-digit",
  });
}

export const STATUS_META = {
  WAITING_FOR_BOT: {
    label: "Waiting on bot",
    color: "amber",
    description: "Queued for the agent to respond",
  },
  AGENT_RESPONDING: {
    label: "Agent responding",
    color: "signal",
    description: "Pipeline is actively processing",
  },
  RESOLVED: {
    label: "Resolved",
    color: "muted",
    description: "No action needed",
  },
  NEEDS_HUMAN: {
    label: "Needs a human",
    color: "coral",
    description: "Handed off — sentiment flagged this conversation",
  },
};

export function initials(name) {
  if (!name) return "?";
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
}
