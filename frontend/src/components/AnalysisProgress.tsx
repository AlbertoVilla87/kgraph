import { Check, Loader2, Circle } from 'lucide-react';

interface Step {
  key: string;
  label: string;
  status: 'pending' | 'running' | 'done';
}

interface AnalysisProgressProps {
  status: {
    progress: number;
    current_step: string;
    detail: string;
    steps: Step[];
  };
}

export default function AnalysisProgress({ status }: AnalysisProgressProps) {
  const pct = Math.round(status.progress * 100);

  return (
    <div className="bg-[var(--color-card)] rounded-xl border border-[var(--color-border)] p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold">Analyzing...</h3>
        <span className="text-sm font-medium text-[var(--color-primary)]">{pct}%</span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden mb-3">
        <div
          className="h-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-purple)] rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Detail text */}
      {status.detail && (
        <p className="text-xs text-[var(--color-text-secondary)] mb-4 font-mono truncate">
          {status.detail}
        </p>
      )}

      {/* Steps */}
      <div className="space-y-3">
        {status.steps.map((step, i) => (
          <div key={step.key} className="flex items-center gap-3">
            {/* Icon */}
            <div className="w-6 h-6 flex items-center justify-center">
              {step.status === 'done' ? (
                <Check size={16} className="text-[var(--color-success)]" />
              ) : step.status === 'running' ? (
                <Loader2 size={16} className="text-[var(--color-primary)] animate-spin" />
              ) : (
                <Circle size={16} className="text-gray-300" />
              )}
            </div>

            {/* Label */}
            <span
              className={`text-sm ${
                step.status === 'done'
                  ? 'text-[var(--color-text-secondary)]'
                  : step.status === 'running'
                  ? 'text-[var(--color-text)] font-medium'
                  : 'text-gray-400'
              }`}
            >
              {step.label}
            </span>

            {/* Connector line */}
            {i < status.steps.length - 1 && (
              <div className="absolute ml-3 mt-8 w-px h-3 bg-gray-200" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
