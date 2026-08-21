import { MetricCard } from '../metrics/MetricCard';
import { GeoChart } from '../charts/GeoChart';
import { DateFilter } from '../filters/DateFilter';
import { SummaryCard } from './SummaryCard';
import { useIntentStore } from '../../store/intentStore';

interface Props {
  onSelect?: (id: string) => void;
}

export function Dashboard({ onSelect }: Props) {
  const {
    highlightIds, clarifyIds, conflictIds, resizedIds,
    lastResponse, dateFilter, compareTargets, explanationText,
  } = useIntentStore();

  const isClarify = lastResponse?.decision === 'clarify';
  const activeSet = new Set(isClarify ? clarifyIds : highlightIds);
  const conflictSet = new Set(conflictIds);
  const anyActive = activeSet.size > 0 || conflictSet.size > 0;

  const props = (id: string) => ({
    highlight: highlightIds.includes(id),
    clarify: clarifyIds.includes(id),
    conflict: conflictIds.includes(id),
    dimmed: anyActive && !activeSet.has(id) && !conflictSet.has(id),
    large: resizedIds.has(id),
    onSelect: isClarify ? onSelect : undefined,
  });

  const metrics = [
    { id: 'revenue', label: 'Revenue', value: '$1.24M', change: '+12.4% vs last month' },
    { id: 'users', label: 'Users', value: '124,582', change: '+8.2% vs last month' },
    { id: 'conversion', label: 'Conversion', value: '7.8%', change: '+0.6pp' },
    { id: 'churn', label: 'Churn', value: '2.4%', change: '-0.3pp' },
    { id: 'retention', label: 'Retention', value: '84%', change: '+2.1pp' },
  ];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold tracking-tight">Analytics Overview</h1>
        <p className="text-slate-400 text-sm mt-1">IntentUI · Multimodal adaptive dashboard</p>
      </header>

      {explanationText && (
        <div className="rounded-xl bg-accent/10 border border-accent/30 p-4" role="status" aria-live="polite">
          <p className="text-sm text-accent-glow font-medium mb-1">Explanation</p>
          <p className="text-slate-200">{explanationText}</p>
        </div>
      )}

      {compareTargets.length >= 2 && (
        <div className="rounded-xl bg-indigo-500/10 border border-indigo-500/30 p-4">
          <p className="text-sm font-medium text-indigo-300">Comparison</p>
          <p className="text-slate-200 mt-1">
            Comparing <strong>{compareTargets[0]}</strong> with <strong>{compareTargets[1]}</strong>
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {metrics.map((m) => (
          <MetricCard key={m.id} {...m} {...props(m.id)} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <GeoChart {...props('geographic')} />
        </div>
        <div className="space-y-4">
          <DateFilter value={dateFilter} {...props('date_filter')} />
          <SummaryCard {...props('summary')} />
        </div>
      </div>
    </div>
  );
}
