"use client";

interface AiSummaryCardProps {
  summary?: string | null;
  actions?: string[] | null;
  risks?: string[] | null;
  source?: string | null;
  generatedAt?: string | null;
  aiAvailable: boolean;
  onGenerate?: () => void;
  isGenerating?: boolean;
  error?: string | null;
  skuLabel: string;
}

const formatTimestamp = (value?: string | null): string | null => {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleString();
};

export function AiSummaryCard({
  summary,
  actions,
  risks,
  source,
  generatedAt,
  aiAvailable,
  onGenerate,
  isGenerating,
  error,
  skuLabel,
}: AiSummaryCardProps) {
  const hasContent = Boolean(summary);
  const formattedTimestamp = formatTimestamp(generatedAt);

  if (!aiAvailable && !hasContent) {
    return null;
  }

  if (!hasContent && aiAvailable) {
    return (
      <div className="mb-6 rounded-lg border border-dashed border-white/20 bg-white/5 p-4 text-sm text-slate-200">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="font-semibold text-white">
              No AI summary generated for {skuLabel}
            </div>
            <p className="text-slate-300">
              Generate on demand when you want AI-backed highlights without slowing the forecast run.
            </p>
          </div>
          {onGenerate && (
            <button
              type="button"
              onClick={onGenerate}
              disabled={isGenerating}
              className="inline-flex items-center gap-2 self-start rounded-full border border-cyan-400/60 bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-400/30 transition hover:translate-y-0.5 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:border-cyan-400/30 disabled:bg-cyan-400/30 disabled:text-slate-800"
            >
              {isGenerating ? "Generating..." : "Generate AI summary"}
            </button>
          )}
        </div>
        {error && (
          <div className="mt-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-rose-100">
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-xl border border-white/10 bg-gradient-to-b from-white/5 via-white/[0.03] to-slate-950/80 p-5 shadow-[0_20px_70px_-30px_rgba(15,23,42,0.7)]">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-white">AI Forecast Summary</h3>
          <p className="text-sm text-slate-300">Highlights generated for {skuLabel}</p>
        </div>
        <div className="flex flex-col items-end gap-2 sm:flex-row sm:items-center sm:gap-3">
          {onGenerate && (
            <button
              type="button"
              onClick={onGenerate}
              disabled={isGenerating}
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-semibold text-slate-100 transition hover:translate-y-0.5 hover:bg-white/10 disabled:cursor-not-allowed disabled:border-white/5 disabled:bg-white/5 disabled:text-slate-500"
            >
              {isGenerating ? "Refreshing..." : "Regenerate"}
            </button>
          )}
          {(source || formattedTimestamp) && (
            <div className="flex flex-col items-start text-xs text-slate-300 sm:items-end">
              {source && (
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 font-medium text-slate-100">
                  {source}
                </span>
              )}
              {formattedTimestamp && (
                <span className="mt-1 text-slate-400">
                  Generated {formattedTimestamp}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-3 rounded-md border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-xs text-rose-100">
          {error}
        </div>
      )}

      <p className="mt-4 text-sm leading-relaxed text-slate-200">{summary}</p>

      {Array.isArray(actions) && actions.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-white">Recommended Actions</h4>
          <ul className="mt-2 space-y-1 text-sm text-slate-200">
            {actions.map((action, index) => (
              <li
                key={`${action}-${index}`}
                className="flex items-start gap-2 rounded-md border border-white/10 bg-white/5 p-2"
              >
                <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-cyan-400" />
                <span>{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {Array.isArray(risks) && risks.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-300/40 bg-amber-400/10 p-3">
          <h4 className="text-sm font-semibold text-amber-50">Risks To Monitor</h4>
          <ul className="mt-2 space-y-1 text-sm text-amber-100">
            {risks.map((risk, index) => (
              <li key={`${risk}-${index}`} className="flex gap-2">
                <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-amber-400" />
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
