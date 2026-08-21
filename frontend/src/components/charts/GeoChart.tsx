import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const DATA = [
  { region: 'India', value: 42 },
  { region: 'US', value: 28 },
  { region: 'Europe', value: 18 },
  { region: 'APAC', value: 12 },
];

interface Props {
  highlight?: boolean;
  clarify?: boolean;
  conflict?: boolean;
  dimmed?: boolean;
  onSelect?: (id: string) => void;
}

export function GeoChart({ highlight, clarify, conflict, dimmed, onSelect }: Props) {
  return (
    <div
      data-intent-id="geographic"
      data-intent-label="Geographic Distribution"
      data-intent-type="chart"
      className={`rounded-xl bg-surface-card border border-surface-border p-5 h-64 cursor-pointer transition-all
        ${highlight ? 'intent-highlight' : ''} ${clarify ? 'intent-clarify' : ''}
        ${conflict ? 'intent-conflict' : ''} ${dimmed ? 'intent-dimmed' : ''}`}
      onClick={() => onSelect?.('geographic')}
      role="button"
      tabIndex={0}
      aria-label="Geographic Distribution"
    >
      <h3 className="text-sm font-medium text-slate-400 mb-4">Geographic Distribution</h3>
      <ResponsiveContainer width="100%" height="85%">
        <BarChart data={DATA}>
          <XAxis dataKey="region" stroke="#64748b" fontSize={12} />
          <YAxis stroke="#64748b" fontSize={12} unit="%" />
          <Tooltip contentStyle={{ background: '#1a2332', border: '1px solid #2a3544' }} />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {DATA.map((_, i) => (
              <Cell key={i} fill={['#3b82f6', '#6366f1', '#8b5cf6', '#a78bfa'][i]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
