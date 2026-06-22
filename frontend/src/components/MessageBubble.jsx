import { FileText, ImageOff, Megaphone, Clock } from "lucide-react";
import { formatClockTime } from "../lib/format";

/**
 * Renders the media portion of a message bubble.
 * Shows an inline image with graceful fallback, or a PDF download badge.
 */
function MediaContent({ message }) {
  if (message.content_type === "image") {
    return (
      <div className="mb-1.5 rounded-md overflow-hidden border border-border-soft bg-ink/40 max-w-[260px]">
        <img
          src={message.media_url}
          alt={message.text || "Shared image"}
          className="w-full h-auto block"
          loading="lazy"
          onError={(e) => {
            e.currentTarget.style.display = "none";
            e.currentTarget.nextSibling.style.display = "flex";
          }}
        />
        {/* Fallback shown when the image URL is unavailable */}
        <div className="hidden items-center gap-2 px-3 py-4 text-faint text-xs">
          <ImageOff size={14} />
          Image unavailable
        </div>
      </div>
    );
  }

  if (message.content_type === "document") {
    return (
      <a
        href={message.media_url}
        target="_blank"
        rel="noreferrer"
        className="mb-1.5 flex items-center gap-2.5 rounded-md border border-border-soft bg-ink/40 px-3 py-2.5 max-w-[260px] hover:bg-ink/60 transition-colors group"
        title="Open document"
      >
        <span className="w-8 h-8 rounded bg-surface flex items-center justify-center shrink-0 group-hover:bg-signal/10 transition-colors">
          <FileText size={15} className="text-muted group-hover:text-signal transition-colors" />
        </span>
        <span className="min-w-0">
          <span className="block text-xs font-medium text-paper truncate">
            {message.media_filename || "Document"}
          </span>
          <span className="block text-[10px] text-faint font-mono">PDF · tap to open</span>
        </span>
      </a>
    );
  }

  return null;
}

/**
 * Metadata row shown at the bottom of each bubble.
 * For bot messages, shows the clock time plus a small "bot replied" indicator.
 * The TypingBubble component (shown live during processing) transitions into
 * this static bubble once the LangGraph dispatcher node completes.
 */
function BubbleMeta({ message }) {
  const isBot = message.sender === "bot";
  const isBroadcast = message.sender === "broadcast";

  return (
    <div className="flex items-center justify-end gap-1.5 mt-1">
      {(isBot || isBroadcast) && (
        <span
          className="text-[9px] font-mono text-faint/60 uppercase tracking-wider"
          title="Delivered by the AI agent"
        >
          {isBroadcast ? "broadcast" : "bot"}
        </span>
      )}
      <span className="text-[10px] font-mono text-faint">
        {formatClockTime(message.timestamp)}
      </span>
      {/* Typing-state metadata: shows when the agent was in typing state before this reply */}
      {isBot && message.status !== "FAILED" && (
        <Clock
          size={9}
          className="text-faint/50"
          title="Message was preceded by a typing indicator"
        />
      )}
    </div>
  );
}

/**
 * A single message bubble in the chat thread.
 *
 * Direction semantics:
 *   inbound  (direction="inbound") → left-aligned, customer bubble
 *   outbound (direction="outbound") → right-aligned
 *     sender="bot"       → agent reply (green tint)
 *     sender="broadcast" → campaign message (amber tint with Broadcast badge)
 *     sender="system"    → centered system notice (e.g. "session started")
 */
export default function MessageBubble({ message }) {
  const isOutbound = message.direction === "outbound";
  const isBroadcast = message.sender === "broadcast";
  const isSystem = message.sender === "system";
  const isFailed = message.status === "FAILED";

  // System notices (session state changes, etc.) render as a centered pill
  if (isSystem) {
    return (
      <div className="flex justify-center my-2 animate-fade-in">
        <span className="text-[11px] font-mono text-faint bg-surface-raised border border-border-soft rounded-full px-3 py-1">
          {message.text}
        </span>
      </div>
    );
  }

  return (
    <div className={`flex ${isOutbound ? "justify-end" : "justify-start"} animate-fade-in`}>
      <div
        className={[
          "max-w-[78%] rounded-lg px-3.5 py-2.5 transition-opacity",
          isFailed ? "opacity-60" : "",
          isOutbound
            ? isBroadcast
              ? "bg-surface-raised border border-amber/25"
              : "bg-signal/10 border border-signal/20"
            : "bg-surface-raised border border-border",
        ].join(" ")}
      >
        {/* Broadcast campaign badge */}
        {isBroadcast && (
          <div className="flex items-center gap-1.5 mb-1.5 text-amber text-[10px] font-mono uppercase tracking-wide">
            <Megaphone size={11} />
            Broadcast
          </div>
        )}

        {/* Media (image thumbnail or PDF badge) */}
        <MediaContent message={message} />

        {/* Text body */}
        {message.text && (
          <p className="text-[13.5px] leading-relaxed text-paper whitespace-pre-wrap break-words">
            {message.text}
          </p>
        )}

        {/* Failed delivery notice */}
        {isFailed && (
          <p className="text-[10px] text-coral font-mono mt-1">⚠ delivery failed</p>
        )}

        {/* Timestamp + metadata row */}
        <BubbleMeta message={message} />
      </div>
    </div>
  );
}
