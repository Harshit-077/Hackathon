interface Props {
  highlight?: boolean;
  clarify?: boolean;
  conflict?: boolean;
  dimmed?: boolean;
  onSelect?: (id: string) => void;
}

export function SummaryCard({ highlight, clarify, conflict, dimmed, onSelect }: Props) {
  return (
    <div
      data-intent-id="summary"
      data-intent-label="Summary Card"
      data-intent-type="summary"
      data-intent-value="Business performance overview"
      className={`rounded-xl bg-gradient-to-br from-surface-card to-surface-border/30 border border-surface-border p-5 cursor-pointer transition-all
        ${highlight ? 'intent-highlight' : ''} ${clarify ? 'intent-clarify' : ''}
        ${conflict ? 'intent-conflict' : ''} ${dimmed ? 'intent-dimmed' : ''}`}
      onClick={() => onSelect?.('summary')}
      role="button"
      tabIndex={0}
      aria-label="Summary Card"
    >
      <h3 className="text-sm font-medium text-slate-400">Summary</h3>
      <p className="text-lg font-semibold mt-2" data-intent-value>Business performance overview</p>
      <p className="text-sm text-slate-400 mt-2">Revenue up 12% · Retention stable · Churn down</p>
    </div>
  );
}
