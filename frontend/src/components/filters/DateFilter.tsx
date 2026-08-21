interface Props {
  value: string;
  highlight?: boolean;
  clarify?: boolean;
  conflict?: boolean;
  dimmed?: boolean;
  onSelect?: (id: string) => void;
}

export function DateFilter({ value, highlight, clarify, conflict, dimmed, onSelect }: Props) {
  return (
    <div
      data-intent-id="date_filter"
      data-intent-label="Date Filter"
      data-intent-type="control"
      data-intent-value={value}
      className={`rounded-xl bg-surface-card border border-surface-border p-4 flex items-center justify-between cursor-pointer transition-all
        ${highlight ? 'intent-highlight' : ''} ${clarify ? 'intent-clarify' : ''}
        ${conflict ? 'intent-conflict' : ''} ${dimmed ? 'intent-dimmed' : ''}`}
      onClick={() => onSelect?.('date_filter')}
      role="button"
      tabIndex={0}
      aria-label="Date Filter"
    >
      <span className="text-sm text-slate-400">Date range</span>
      <span className="text-sm font-semibold text-accent" data-intent-value>{value}</span>
    </div>
  );
}
