import type { ReactNode } from 'react';

interface Props {
  id: string;
  label: string;
  type: string;
  value?: string;
  children: ReactNode;
  className?: string;
  highlight?: boolean;
  clarify?: boolean;
  conflict?: boolean;
  dimmed?: boolean;
  large?: boolean;
  onSelect?: (id: string) => void;
}

export function IntentElement({
  id, label, type, value, children, className = '',
  highlight, clarify, conflict, dimmed, large, onSelect,
}: Props) {
  const ring = conflict ? 'intent-conflict' : clarify ? 'intent-clarify' : highlight ? 'intent-highlight' : '';
  const size = large ? 'intent-resize-large' : '';

  return (
    <div
      data-intent-id={id}
      data-intent-label={label}
      data-intent-type={type}
      data-intent-value={value}
      className={`relative rounded-xl bg-surface-card border border-surface-border p-5 transition-all duration-300 ${ring} ${dimmed ? 'intent-dimmed' : ''} ${size} ${className}`}
      onClick={() => onSelect?.(id)}
      role="button"
      tabIndex={0}
      aria-label={label}
      onKeyDown={(e) => { if (e.key === 'Enter') onSelect?.(id); }}
    >
      {children}
    </div>
  );
}
