import { useState } from "react";
import { X, Megaphone, Loader2, CheckCircle2 } from "lucide-react";
import { api } from "../api/client";

const COHORTS = [
  { key: "all", label: "Everyone", hint: "Every customer with a conversation on this line" },
  { key: "needs_human", label: "Needs a human", hint: "Currently flagged for handover" },
  { key: "resolved", label: "Resolved this week", hint: "Conversations the bot already closed out" },
  { key: "custom", label: "Custom numbers", hint: "Paste specific phone numbers" },
];

export default function BroadcastDrawer({ open, onClose, tenant }) {
  const [cohort, setCohort] = useState("all");
  const [customNumbers, setCustomNumbers] = useState("");
  const [templateName, setTemplateName] = useState("catalog_promo");
  const [previewText, setPreviewText] = useState(
    "New arrivals just dropped! Reply catalog to see what's new."
  );
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  async function handleSend() {
    if (!tenant) return;
    setSending(true);
    setError(null);
    setResult(null);
    try {
      const phone_numbers = customNumbers
        .split(/[\n,]/)
        .map((n) => n.trim())
        .filter(Boolean);
      const res = await api.broadcast(tenant.tenant_id, {
        cohort,
        phone_numbers,
        template_name: templateName.trim() || "catalog_promo",
        preview_text: previewText,
      });
      setResult(res);
    } catch (err) {
      setError(err.message || "Broadcast failed.");
    } finally {
      setSending(false);
    }
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div className="absolute inset-0 bg-ink/70 backdrop-blur-[2px]" onClick={onClose} />
      <div className="relative w-full max-w-md bg-surface border-l border-border h-full flex flex-col animate-slide-in">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Megaphone size={15} className="text-signal" />
            <h3 className="font-display font-semibold text-[14px] text-paper">Broadcast campaign</h3>
          </div>
          <button onClick={onClose} className="text-faint hover:text-paper transition-colors">
            <X size={17} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
          <p className="text-[12px] text-muted leading-relaxed">
            Send a template message to a cohort of {tenant?.name || "this tenant"}'s customers. This
            uses WhatsApp's outbound template flow, the only message type allowed outside the 24-hour
            customer-service window.
          </p>

          <div>
            <label className="block text-[10px] font-mono uppercase tracking-wide text-faint mb-2">
              Audience
            </label>
            <div className="space-y-1.5">
              {COHORTS.map((c) => (
                <button
                  key={c.key}
                  onClick={() => setCohort(c.key)}
                  className={[
                    "w-full text-left px-3 py-2.5 rounded-md border transition-colors",
                    cohort === c.key
                      ? "border-signal/40 bg-signal/10"
                      : "border-border-soft bg-surface-raised hover:border-faint/40",
                  ].join(" ")}
                >
                  <p className={`text-[12.5px] font-medium ${cohort === c.key ? "text-signal" : "text-paper"}`}>
                    {c.label}
                  </p>
                  <p className="text-[11px] text-faint mt-0.5">{c.hint}</p>
                </button>
              ))}
            </div>
          </div>

          {cohort === "custom" && (
            <div>
              <label className="block text-[10px] font-mono uppercase tracking-wide text-faint mb-1.5">
                Phone numbers (one per line, or comma-separated)
              </label>
              <textarea
                value={customNumbers}
                onChange={(e) => setCustomNumbers(e.target.value)}
                rows={3}
                placeholder={"+15551234567\n+15557654321"}
                className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-[12.5px] font-mono text-paper placeholder:text-faint outline-none focus:border-signal/50"
              />
            </div>
          )}

          <div>
            <label className="block text-[10px] font-mono uppercase tracking-wide text-faint mb-1.5">
              Template name
            </label>
            <input
              value={templateName}
              onChange={(e) => setTemplateName(e.target.value)}
              className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-[12.5px] font-mono text-paper outline-none focus:border-signal/50"
            />
          </div>

          <div>
            <label className="block text-[10px] font-mono uppercase tracking-wide text-faint mb-1.5">
              Preview text
            </label>
            <textarea
              value={previewText}
              onChange={(e) => setPreviewText(e.target.value)}
              rows={2}
              className="w-full bg-surface-raised border border-border rounded-md px-3 py-2 text-[12.5px] text-paper outline-none focus:border-signal/50"
            />
          </div>

          {result && (
            <div className="flex items-start gap-2 px-3 py-2.5 rounded-md bg-signal/10 border border-signal/25">
              <CheckCircle2 size={14} className="text-signal shrink-0 mt-0.5" />
              <p className="text-[12px] text-paper">
                Sent to <span className="font-mono">{result.sent}</span> customer
                {result.sent === 1 ? "" : "s"}.
                {result.note && <span className="block text-faint mt-0.5">{result.note}</span>}
              </p>
            </div>
          )}
          {error && (
            <div className="px-3 py-2.5 rounded-md bg-coral/10 border border-coral/25 text-[12px] text-coral">
              {error}
            </div>
          )}
        </div>

        <div className="px-5 py-4 border-t border-border">
          <button
            onClick={handleSend}
            disabled={sending || !tenant}
            className="w-full flex items-center justify-center gap-2 bg-signal text-ink font-medium text-[13px] py-2.5 rounded-md hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            {sending ? <Loader2 size={14} className="animate-spin" /> : <Megaphone size={14} />}
            {sending ? "Sending…" : "Send broadcast"}
          </button>
        </div>
      </div>
    </div>
  );
}
