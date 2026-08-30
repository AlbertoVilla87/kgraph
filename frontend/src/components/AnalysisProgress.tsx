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
  const running = status.steps.find((s) => s.status === 'running');

  return (
    <div className="glass rounded-2xl px-4 py-3">
      <div className="flex items-center justify-between gap-4 mb-2.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <Loader2 size={14} className="text-[var(--color-primary)] animate-spin shrink-0" />
          <span className="text-sm font-medium shrink-0">Analyzing</span>
          {running && (
            <span className="text-xs text-[var(--color-text-secondary)] truncate">
              {running.label}…
            </span>
          )}
        </div>
        <span className="font-mono text-sm text-[var(--color-primary)] tabular-nums">{pct}%</span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1.5 bg-[var(--color-surface-3)] rounded-full overflow-hidden mb-2.5">
        <div
          className="h-full bg-gradient-to-r from-[var(--color-primary)] to-[var(--color-cobalt)] rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%`, boxShadow: '0 0 12px var(--color-primary-glow)' }}
        />
      </div>

      {status.detail && (
        <p className="text-[11px] text-[var(--color-text-faint)] font-mono truncate mb-2.5">
          {status.detail}
        </p>
      )}

      {/* Steps trail */}
      <div className="flex items-center gap-1 overflow-x-auto no-scrollbar">
        {status.steps.map((step, i) => (
          <div key={step.key} className="flex items-center gap-1 shrink-0">
            {i > 0 && (
              <div className={`w-6 h-px ${step.status === 'pending' ? 'bg-[var(--color-line)]' : 'bg-[var(--color-primary-glow)]'}`} />
            )}
            <div className="flex items-center gap-1.5">
              {step.status === 'done' ? (
                <span className="w-[18px] h-[18px] rounded-full flex items-center justify-center bg-[var(--color-primary-soft)]">
                  <Check size={11} className="text-[var(--color-primary)]" />
                </span>
              ) : step.status === 'running' ? (
                <Loader2 size={15} className="text-[var(--color-primary)] animate-spin" />
              ) : (
                <Circle size={14} className="text-[var(--color-text-faint)]" />
              )}
              <span
                className={`text-[11px] whitespace-nowrap ${
                  step.status === 'done'
                    ? 'text-[var(--color-text-faint)]'
                    : step.status === 'running'
                      ? 'text-[var(--color-text)] font-medium'
                      : 'text-[var(--color-text-faint)]'
                }`}
              >
                {step.label}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}