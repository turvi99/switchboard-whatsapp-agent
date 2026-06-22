import { useState } from "react";
import { Send, Image as ImageIcon, FlaskConical } from "lucide-react";
import { api } from "../api/client";

export default function SimulatorComposer({ tenantId, customerPhone, onSent, disabled }) {
  const [text, setText] = useState("");
  const [withImage, setWithImage] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!text.trim() && !withImage) return;
    setSending(true);
    setError(null);
    try {
      await api.simulateInbound({
        tenant_id: tenantId,
        customer_phone: customerPhone,
        text: text.trim() || (withImage ? "Sent a photo" : ""),
        simulate_image: withImage,
      });
      setText("");
      setWithImage(false);
      onSent?.();
    } catch (err) {
      setError(err.message || "Couldn't send that.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="border-t border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-1.5 mb-2 text-[10px] font-mono uppercase tracking-wide text-faint">
        <FlaskConical size={11} />
        Simulate inbound — no real WhatsApp number needed
      </div>
      <form onSubmit={handleSubmit} className="flex items-end gap-2">
        <button
          type="button"
          onClick={() => setWithImage((v) => !v)}
          disabled={disabled}
          title="Attach a simulated image"
          className={[
            "shrink-0 w-9 h-9 rounded-md border flex items-center justify-center transition-colors",
            withImage
              ? "bg-signal/15 border-signal/40 text-signal"
              : "bg-surface-raised border-border text-muted hover:text-paper hover:border-faint",
          ].join(" ")}
        >
          <ImageIcon size={15} />
        </button>
        <textarea
          rows={1}
          value={text}
          disabled={disabled}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit(e);
            }
          }}
          placeholder={withImage ? "Optional caption for the test image…" : "Type a message as this customer…"}
          className="flex-1 resize-none bg-surface-raised border border-border rounded-md px-3 py-2 text-[13.5px] text-paper placeholder:text-faint focus:border-signal/50 outline-none disabled:opacity-50 max-h-24"
        />
        <button
          type="submit"
          disabled={disabled || sending || (!text.trim() && !withImage)}
          className="shrink-0 w-9 h-9 rounded-md bg-signal text-ink flex items-center justify-center transition-opacity hover:opacity-90 disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Send size={15} />
        </button>
      </form>
      {error && <p className="mt-1.5 text-[11px] text-coral font-mono">{error}</p>}
    </div>
  );
}
