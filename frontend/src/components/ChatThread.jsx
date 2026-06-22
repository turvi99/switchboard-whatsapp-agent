import { useEffect, useRef, useState } from "react";
import { Phone, FlaskConical, Send, MessageSquareDashed } from "lucide-react";
import PipelineStrip from "./PipelineStrip";
import MessageBubble from "./MessageBubble";
import TypingBubble from "./TypingBubble";
import StatusPill from "./StatusPill";
import SimulatorComposer from "./SimulatorComposer";
import { formatPhone } from "../lib/format";
import { api } from "../api/client";

const TENANT_ACCENT_TEXT = {
  "#C8A24A": "text-tenant-gold",
  "#3E7CB1": "text-tenant-steel",
};

function NewConversationStarter({ tenantId, onStarted }) {
  const [phone, setPhone] = useState("+1555");
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!phone.trim() || !text.trim()) return;
    setSending(true);
    setError(null);
    try {
      await api.simulateInbound({ tenant_id: tenantId, customer_phone: phone.trim(), text: text.trim() });
      onStarted?.(phone.trim());
      setText("");
    } catch (err) {
      setError(err.message || "Couldn't start that conversation.");
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="w-full max-w-sm">
      <div className="flex items-center gap-1.5 mb-3 text-[10px] font-mono uppercase tracking-wide text-faint justify-center">
        <FlaskConical size={11} />
        Start a test conversation
      </div>
      <form onSubmit={handleSubmit} className="space-y-2">
        <div className="flex items-center gap-2 bg-surface-raised border border-border rounded-md px-3 py-2 focus-within:border-signal/50">
          <Phone size={13} className="text-faint shrink-0" />
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="+15551234567"
            className="bg-transparent text-[13px] font-mono text-paper placeholder:text-faint outline-none w-full"
          />
        </div>
        <div className="flex items-center gap-2 bg-surface-raised border border-border rounded-md px-3 py-2 focus-within:border-signal/50">
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="What does this customer say?"
            className="bg-transparent text-[13px] text-paper placeholder:text-faint outline-none w-full"
          />
          <button
            type="submit"
            disabled={sending || !phone.trim() || !text.trim()}
            className="shrink-0 w-7 h-7 rounded bg-signal text-ink flex items-center justify-center disabled:opacity-30"
          >
            <Send size={13} />
          </button>
        </div>
      </form>
      {error && <p className="mt-2 text-[11px] text-coral font-mono text-center">{error}</p>}
    </div>
  );
}

export default function ChatThread({ tenant, session, messages, liveEvent, onRefresh, onNewConversation }) {
  const scrollRef = useRef(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const processingTimeout = useRef(null);

  useEffect(() => {
    if (!liveEvent || !session || liveEvent.session_id !== session.session_id) return;
    setIsProcessing(true);
    clearTimeout(processingTimeout.current);
    const terminal = liveEvent.node === "dispatcher" || liveEvent.node === "human_handover";
    processingTimeout.current = setTimeout(() => setIsProcessing(false), terminal ? 1100 : 6000);
  }, [liveEvent, session]);

  useEffect(() => () => clearTimeout(processingTimeout.current), []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isProcessing]);

  if (!session) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-6 bg-ink px-6">
        <div className="text-center">
          <MessageSquareDashed size={28} className="text-faint mx-auto mb-3" />
          <p className="text-sm text-muted">Select a conversation to view the wire.</p>
        </div>
        {tenant && <NewConversationStarter tenantId={tenant.tenant_id} onStarted={onNewConversation} />}
      </div>
    );
  }

  const liveForSession = liveEvent && liveEvent.session_id === session.session_id ? liveEvent : null;
  const accentText = TENANT_ACCENT_TEXT[tenant?.brand_color] || "text-signal";

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-ink">
      <div className="px-5 py-3.5 border-b border-border flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={`text-[11px] font-mono uppercase tracking-wide ${accentText}`}>
              {tenant?.name}
            </span>
          </div>
          <h2 className="font-display font-semibold text-[15px] text-paper truncate">
            {formatPhone(session.customer_phone)}
          </h2>
        </div>
        <StatusPill status={session.status} size="md" />
      </div>

      <PipelineStrip
        activeNode={liveForSession?.node}
        trace={liveForSession?.trace || []}
        isProcessing={isProcessing}
      />

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-center text-xs text-faint mt-8">No messages yet on this thread.</p>
        )}
        {messages.map((m) => (
          <MessageBubble key={m.message_id} message={m} />
        ))}
        {isProcessing && session.status !== "RESOLVED" && session.status !== "NEEDS_HUMAN" && <TypingBubble />}
      </div>

      <SimulatorComposer
        tenantId={tenant?.tenant_id}
        customerPhone={session.customer_phone}
        onSent={onRefresh}
      />
    </div>
  );
}
