export default function TypingBubble() {
  return (
    <div className="flex justify-start animate-fade-in">
      <div className="bg-surface-raised border border-border rounded-lg px-4 py-3 flex items-center gap-1">
        <span className="w-1.5 h-1.5 rounded-full bg-muted animate-pulse-dot" style={{ animationDelay: "0ms" }} />
        <span className="w-1.5 h-1.5 rounded-full bg-muted animate-pulse-dot" style={{ animationDelay: "200ms" }} />
        <span className="w-1.5 h-1.5 rounded-full bg-muted animate-pulse-dot" style={{ animationDelay: "400ms" }} />
      </div>
    </div>
  );
}
