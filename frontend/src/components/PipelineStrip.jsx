import { Fragment } from "react";
import { Eye, Database, Cpu, Send, UserCog } from "lucide-react";

// The four nodes from the assignment's required pipeline. "dispatcher" swaps
// its label/icon/color to "Handover" when the bonus sentiment-handover path
// fires, since human_handover is the alternate terminal node in the graph.
const STAGE_ORDER = ["acknowledge", "context_retriever", "llm_reasoning", "dispatcher"];

const STAGE_META = {
  acknowledge: { label: "Acknowledge", icon: Eye },
  context_retriever: { label: "Context", icon: Database },
  llm_reasoning: { label: "Reasoning", icon: Cpu },
  dispatcher: { label: "Dispatch", icon: Send },
};

// Tailwind's JIT scanner needs literal class names, not interpolated ones -
// so accent variants are precomputed here rather than built with template
// strings like `bg-${accent}` (which would silently fail to generate CSS).
const ACCENT = {
  signal: {
    text: "text-signal",
    dot: "bg-signal",
    bar: "bg-signal",
    glow: "0 0 6px 2px rgba(61,220,132,0.55)",
    nodeActive: "bg-signal/15 border-signal text-signal animate-pulse-dot",
  },
  coral: {
    text: "text-coral",
    dot: "bg-coral",
    bar: "bg-coral",
    glow: "0 0 6px 2px rgba(255,93,93,0.55)",
    nodeActive: "bg-coral/15 border-coral text-coral animate-pulse-dot",
  },
};

export default function PipelineStrip({ activeNode, trace = [], isProcessing }) {
  const isHandover = activeNode === "human_handover" || trace.includes("human_handover");
  const effectiveActive = activeNode === "human_handover" ? "dispatcher" : activeNode;
  const activeIndex = STAGE_ORDER.indexOf(effectiveActive);
  const accentKey = isHandover ? "coral" : "signal";
  const accent = ACCENT[accentKey];

  return (
    <div className="px-5 py-3.5 bg-surface-raised border-b border-border">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[10px] font-mono uppercase tracking-[0.14em] text-faint">
          Agent pipeline
        </span>
        {isProcessing && (
          <span className={`text-[10px] font-mono uppercase tracking-wide flex items-center gap-1.5 ${accent.text}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${accent.dot} animate-pulse-dot`} />
            running
          </span>
        )}
      </div>
      <div className="flex items-start">
        {STAGE_ORDER.map((key, i) => {
          const meta = key === "dispatcher" && isHandover ? { label: "Handover", icon: UserCog } : STAGE_META[key];
          const Icon = meta.icon;
          const isDone = activeIndex === -1 ? trace.includes(key) : activeIndex > i;
          const isActive = i === activeIndex;

          return (
            <Fragment key={key}>
              <div className="flex flex-col items-center gap-1.5 w-[72px] shrink-0">
                <div
                  className={[
                    "w-7 h-7 rounded-full border flex items-center justify-center transition-colors duration-300",
                    isActive
                      ? accent.nodeActive
                      : isDone
                      ? "bg-faint/10 border-faint/50 text-muted"
                      : "bg-transparent border-border text-faint",
                  ].join(" ")}
                >
                  <Icon size={13} strokeWidth={2.25} />
                </div>
                <span
                  className={[
                    "text-[10px] font-mono uppercase tracking-wide text-center leading-tight",
                    isActive ? accent.text : isDone ? "text-muted" : "text-faint",
                  ].join(" ")}
                >
                  {meta.label}
                </span>
              </div>
              {i < STAGE_ORDER.length - 1 && (
                <div className="relative flex-1 h-px bg-border mt-3.5 overflow-visible">
                  <div
                    className={`absolute inset-y-0 left-0 ${accent.bar} transition-all duration-500 ease-out`}
                    style={{ width: isDone || activeIndex > i ? "100%" : "0%" }}
                  />
                  {isProcessing && isActive && (
                    <div
                      className={`absolute top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full ${accent.dot} animate-travel-dot`}
                      style={{ boxShadow: accent.glow }}
                    />
                  )}
                </div>
              )}
            </Fragment>
          );
        })}
      </div>
    </div>
  );
}
