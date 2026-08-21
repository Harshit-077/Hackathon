interface Props {
  id: string;
  label: string;
  value: string;
  change: string;
  highlight?: boolean;
  clarify?: boolean;
  conflict?: boolean;
  dimmed?: boolean;
  large?: boolean;
  onSelect?: (id: string) => void;
}

export function MetricCard({
  id, label, value, change,
  highlight, clarify, conflict, dimmed, large, onSelect,
}: Props) {
  return (
    <div
      data-intent-id={id}
      data-intent-label={label}
      data-intent-type="metric_card"
      data-intent-value={value}
      className={`rounded-xl bg-surface-card border border-surface-border p-5 cursor-pointer transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent
        ${highlight ? 'intent-highlight' : ''}
        ${clarify ? 'intent-clarify' : ''}
        ${conflict ? 'intent-conflict' : ''}
        ${dimmed ? 'intent-dimmed' : ''}
        ${large ? 'intent-resize-large !col-span-2' : ''}`}
      onClick={() => onSelect?.(id)}
      role="button"
      tabIndex={0}
      aria-pressed={clarify || highlight || conflict}
      aria-label={label}
      onKeyDown={(e) => { if (e.key === 'Enter') onSelect?.(id); }}
    >
      <p className="text-sm text-slate-400 font-medium">{label}</p>
      <p className="text-3xl font-bold mt-1 tracking-tight" data-intent-value>{value}</p>
      <p className={`text-sm mt-2 ${change.startsWith('+') ? 'text-emerald-400' : 'text-rose-400'}`}>{change}</p>
    </div>
  );
}
