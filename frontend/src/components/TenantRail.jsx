import { initials } from "../lib/format";

const ACCENT_BG = {
  "#C8A24A": "bg-tenant-gold/15 border-tenant-gold text-tenant-gold",
  "#3E7CB1": "bg-tenant-steel/15 border-tenant-steel text-tenant-steel",
};
const ACCENT_BAR = {
  "#C8A24A": "bg-tenant-gold",
  "#3E7CB1": "bg-tenant-steel",
};

export default function TenantRail({ tenants, selectedId, onSelect }) {
  return (
    <div className="w-[72px] shrink-0 bg-surface border-r border-border flex flex-col items-center py-4">
      <div className="flex flex-col items-center gap-2.5">
        {tenants.map((t) => {
          const isSelected = t.tenant_id === selectedId;
          const accent = ACCENT_BG[t.brand_color] || "bg-signal/15 border-signal text-signal";
          const bar = ACCENT_BAR[t.brand_color] || "bg-signal";
          return (
            <button
              key={t.tenant_id}
              onClick={() => onSelect(t)}
              title={t.name}
              className="relative group"
            >
              {isSelected && (
                <span className={`absolute -left-[13px] top-1/2 -translate-y-1/2 w-1 h-6 rounded-full ${bar}`} />
              )}
              <div
                className={[
                  "w-10 h-10 rounded-lg border flex items-center justify-center font-display font-semibold text-[12px] transition-all",
                  isSelected ? accent : "bg-surface-raised border-border text-muted group-hover:text-paper group-hover:border-faint/50",
                ].join(" ")}
              >
                {initials(t.name)}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
