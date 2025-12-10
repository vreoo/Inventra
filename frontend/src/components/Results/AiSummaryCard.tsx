"use client";

interface AiSummaryCardProps {
  summary?: string | null;
  actions?: string[] | null;
  risks?: string[] | null;
  source?: string | null;
  generatedAt?: string | null;
  featureEnabled: boolean;
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
  featureEnabled,
  skuLabel,
}: AiSummaryCardProps) {
  const hasContent = Boolean(summary);
  const formattedTimestamp = formatTimestamp(generatedAt);

  if (!hasContent && !featureEnabled) {
    return null;
  }

  if (!hasContent && featureEnabled) {
    return (
      <div className="mb-6 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-4 text-sm text-slate-600">
        AI summary is enabled for {skuLabel}, but no explanation was generated.
        This usually resolves once the forecast is re-run or the AI service is
        available again.
      </div>
    );
  }

  return (
    <div className="mb-6 rounded-lg border border-indigo-100 bg-indigo-50 p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-indigo-900">
            AI Forecast Summary
          </h3>
          <p className="text-sm text-indigo-700">
            Highlights generated for {skuLabel}
          </p>
        </div>
        {(source || formattedTimestamp) && (
          <div className="flex flex-col items-start text-xs text-indigo-700 sm:items-end">
            {source && (
              <span className="rounded-full bg-indigo-100 px-3 py-1 font-medium">
                {source}
              </span>
            )}
            {formattedTimestamp && (
              <span className="mt-1 text-indigo-600">
                Generated {formattedTimestamp}
              </span>
            )}
          </div>
        )}
      </div>

      <p className="mt-4 text-sm leading-relaxed text-indigo-900">{summary}</p>

      {Array.isArray(actions) && actions.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-semibold text-indigo-900">
            Recommended Actions
          </h4>
          <ul className="mt-2 space-y-1 text-sm text-indigo-900">
            {actions.map((action, index) => (
              <li
                key={`${action}-${index}`}
                className="flex items-start gap-2 rounded-md bg-white/80 p-2 shadow-sm"
              >
                <span className="mt-2 h-2 w-2 flex-shrink-0 rounded-full bg-indigo-500" />
                <span>{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {Array.isArray(risks) && risks.length > 0 && (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-50 p-3">
          <h4 className="text-sm font-semibold text-amber-900">
            Risks To Monitor
          </h4>
          <ul className="mt-2 space-y-1 text-sm text-amber-900">
            {risks.map((risk, index) => (
              <li key={`${risk}-${index}`} className="flex gap-2">
                <span className="mt-1 h-2 w-2 flex-shrink-0 rounded-full bg-amber-500" />
                <span>{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
