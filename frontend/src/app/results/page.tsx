"use client";

import { Suspense, useEffect, useState } from "react";
import {
  exportForecast,
  ExportKind,
  getForecastResult,
  ForecastResult,
} from "@/services/api";
import { useSearchParams } from "next/navigation";
import { ExternalFactors } from "@/components/Results/ExternalFactors";
import { Loading } from "@/components/Results/Loading";
import { AiSummaryCard } from "@/components/Results/AiSummaryCard";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type ForecastRangeValue = "7" | "30" | "90" | "365" | "max";

type ForecastViewMode = "list" | "chart";

const FORECAST_RANGE_OPTIONS: Array<{
  label: string;
  value: ForecastRangeValue;
}> = [
  { label: "7 Days", value: "7" },
  { label: "30 Days", value: "30" },
  { label: "90 Days", value: "90" },
  { label: "1 Year", value: "365" },
  { label: "Max", value: "max" },
];

function ResultsPageContent() {
  const searchParams = useSearchParams();
  const jobId = searchParams.get("jobId");
  const [jobData, setJobData] = useState<ForecastResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [forecastRangeSelections, setForecastRangeSelections] = useState<
    Record<string, ForecastRangeValue>
  >({});
  const [forecastViewSelections, setForecastViewSelections] = useState<
    Record<string, ForecastViewMode>
  >({});
  const [exportingKind, setExportingKind] = useState<ExportKind | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const interval = setInterval(async () => {
      try {
        const response = await getForecastResult(jobId);
        console.log("🔍 Forecast Response:", response); // Debug logging
        setJobData(response);

        if (response.status === "COMPLETED" || response.status === "FAILED") {
          clearInterval(interval);
        }
      } catch (err: unknown) {
        console.error("❌ Fetch error:", err); // Debug logging
        setError("Failed to fetch forecast result");
        clearInterval(interval);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [jobId]);

  useEffect(() => {
    if (jobData) {
      const timer = setTimeout(() => {
        setIsLoading(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [jobData]);

  // Replace the existing loading check
  if (!jobData || isLoading) {
    return <Loading />;
  }

  if (error) {
    return (
      <main className="relative isolate min-h-screen overflow-x-hidden bg-slate-950 text-slate-100">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_55%)]" />
        <div className="pointer-events-none absolute -top-72 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,_rgba(56,189,248,0.28)_0,_transparent_65%)] blur-3xl" />
        <div className="relative z-10 mx-auto max-w-5xl px-4 py-12 sm:px-6 lg:px-8">
          <div className="rounded-2xl border border-rose-500/30 bg-rose-500/10 p-6 text-rose-50 shadow-[0_20px_70px_-30px_rgba(15,23,42,0.7)]">
            <p>{error}</p>
          </div>

          {jobData && (
            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5 text-sm text-slate-200">
                <h3 className="text-base font-semibold text-white">
                  Job Context
                </h3>
                <div className="mt-3 space-y-1">
                  <div>
                    Mode:{" "}
                    <span className="font-semibold text-white">
                      {jobData.mode ?? "inventory"}
                    </span>
                  </div>
                  {jobData.schema_version && (
                    <div>
                      Schema version:{" "}
                      <span className="font-semibold text-white">
                        {jobData.schema_version}
                      </span>
                    </div>
                  )}
                  <div>
                    Created: {new Date(jobData.created_at).toLocaleString()}
                  </div>
                  {jobData.completed_at && (
                    <div>
                      Completed: {new Date(jobData.completed_at).toLocaleString()}
                    </div>
                  )}
                </div>
              </div>
              {jobData.validation && (
                <div className="rounded-2xl border border-cyan-400/25 bg-cyan-500/10 p-5 text-sm text-cyan-50">
                  <h3 className="text-base font-semibold text-white">
                    Validation Summary
                  </h3>
                  <div className="mt-3 space-y-1">
                    {jobData.validation.detected_frequency && (
                      <div>
                        Frequency detected:{" "}
                        {jobData.validation.detected_frequency}
                      </div>
                    )}
                    {typeof jobData.validation.date_coverage_pct === "number" && (
                      <div>
                        Date coverage:{" "}
                        {(jobData.validation.date_coverage_pct * 100).toFixed(1)}%
                      </div>
                    )}
                    {jobData.validation.anomalies &&
                      jobData.validation.anomalies.length > 0 && (
                        <div>
                          Anomalies flagged: {jobData.validation.anomalies.length}
                        </div>
                      )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    );
  }

  if (!jobData) {
    return <Loading />;
  }

  const aiSummaryEnabled = Boolean(jobData.config?.enable_ai_summary);
  const canExport =
    jobData.status === "COMPLETED" &&
    Array.isArray(jobData.results) &&
    jobData.results.length > 0;

  const triggerDownload = async (kind: ExportKind) => {
    if (!jobId) return;
    setExportError(null);
    setExportingKind(kind);
    try {
      const { blob, filename } = await exportForecast(jobId, kind);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || `forecast-${jobId}-${kind}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setExportError(
        err instanceof Error
          ? err.message
          : "Failed to export forecast CSV."
      );
    } finally {
      setExportingKind(null);
    }
  };

  return (
    <main className="relative isolate min-h-screen overflow-x-hidden bg-slate-950 text-slate-100">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(56,189,248,0.12),_transparent_55%)]" />
      <div className="pointer-events-none absolute -top-72 left-1/2 h-[520px] w-[520px] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,_rgba(56,189,248,0.28)_0,_transparent_65%)] blur-3xl" />
      <div className="relative z-10 mx-auto max-w-6xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="space-y-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.3em] text-cyan-300">
              Forecast
              <span className="h-1 w-1 rounded-full bg-cyan-300" />
              Results
            </div>
            <h1 className="text-3xl font-semibold text-white sm:text-4xl">
              Forecast Results
            </h1>
            <p className="text-sm text-slate-300">
              Download reorder-ready CSVs, review AI notes, and explore external
              factors in one familiar Inventra view.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={!canExport || exportingKind !== null}
              onClick={() => triggerDownload("orders")}
              className="inline-flex items-center gap-2 rounded-full border border-cyan-400/50 bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-400/30 transition hover:translate-y-0.5 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:border-cyan-400/30 disabled:bg-cyan-400/30 disabled:text-slate-800"
              aria-busy={exportingKind === "orders"}
            >
              {exportingKind === "orders" ? "Exporting..." : "Export order plan"}
            </button>
            <button
              type="button"
              disabled={!canExport || exportingKind !== null}
              onClick={() => triggerDownload("forecast")}
              className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm font-semibold text-slate-100 transition hover:translate-y-0.5 hover:bg-white/10 disabled:cursor-not-allowed disabled:border-white/5 disabled:bg-white/5 disabled:text-slate-500"
              aria-busy={exportingKind === "forecast"}
            >
              {exportingKind === "forecast"
                ? "Exporting..."
                : "Export forecast points"}
            </button>
          </div>
        </div>

        {exportError && (
          <div className="mb-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
            {exportError}
          </div>
        )}

        {/* Job Status */}
        <div className="mb-8">
          <div
            className={`inline-flex items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold ${
              jobData.status === "COMPLETED"
                ? "border border-emerald-400/40 bg-emerald-400/10 text-emerald-200"
                : jobData.status === "FAILED"
                ? "border border-rose-400/40 bg-rose-400/10 text-rose-100"
                : jobData.status === "PROCESSING"
                ? "border border-cyan-400/40 bg-cyan-400/10 text-cyan-100"
                : "border border-amber-300/40 bg-amber-300/10 text-amber-100"
            }`}
          >
            <span className="h-2 w-2 rounded-full bg-current" />
            {jobData.status}
          </div>
          {jobData.error_message && (
            <div className="mt-3 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
              {jobData.error_message}
            </div>
          )}
        </div>

        {jobData.status === "COMPLETED" && jobData.results ? (
          <div className="space-y-8">
            {jobData.results.map((result, index) => {
              const resultKey =
                result.product_id ?? result.product_name ?? index.toString();
              const selectedRange = forecastRangeSelections[resultKey] ?? "7";
              const selectedOption =
                FORECAST_RANGE_OPTIONS.find(
                  (option) => option.value === selectedRange
                ) ?? FORECAST_RANGE_OPTIONS[0];
              const hasForecastPoints =
                Array.isArray(result.forecast_points) &&
                result.forecast_points.length > 0;
              const forecastPointsToShow = hasForecastPoints
                ? selectedRange === "max"
                  ? result.forecast_points
                  : result.forecast_points.slice(0, Number(selectedRange))
                : [];
              const selectedView = forecastViewSelections[resultKey] ?? "list";
              const chartData = forecastPointsToShow.map((point) => ({
                date: point.date,
                forecast: point.forecast === undefined ? null : point.forecast,
                lower:
                  point.lower_bound === undefined ? null : point.lower_bound,
                upper:
                  point.upper_bound === undefined ? null : point.upper_bound,
              }));
              const previewLabel =
                selectedOption.value === "max"
                  ? "All Forecast Points"
                  : `Next ${selectedOption.label}`;

              const modeForResult = result.mode ?? jobData.mode ?? "inventory";
              const isDemandMode = modeForResult === "demand";

              const metricCards: Array<{
                key: string;
                title: string;
                tone: "red" | "blue" | "green" | "purple" | "gray";
                content: string;
              }> = [];

              if (result.stockout_date) {
                metricCards.push({
                  key: "stockout",
                  title: "Projected Stockout",
                  tone: "red",
                  content: result.stockout_date,
                });
              }

              if (typeof result.reorder_point === "number") {
                metricCards.push({
                  key: "reorder_point",
                  title: "Reorder Point",
                  tone: "blue",
                  content: `${result.reorder_point.toFixed(1)} units`,
                });
              }

              if (result.reorder_date) {
                metricCards.push({
                  key: "reorder_date",
                  title: "Next Reorder Date",
                  tone: "purple",
                  content: result.reorder_date,
                });
              }

              if (isDemandMode) {
                if (typeof result.recommended_order_qty === "number") {
                  metricCards.push({
                    key: "recommended_order",
                    title: "Recommended Order Qty",
                    tone: "green",
                    content: `${result.recommended_order_qty.toFixed(0)} units`,
                  });
                }

                if (typeof result.safety_stock === "number") {
                  metricCards.push({
                    key: "safety_stock",
                    title: "Safety Stock",
                    tone: "blue",
                    content: `${result.safety_stock.toFixed(1)} units`,
                  });
                }

                if (typeof result.service_level === "number") {
                  metricCards.push({
                    key: "service_level",
                    title: "Service Level Target",
                    tone: "green",
                    content: `${(result.service_level * 100).toFixed(1)}%`,
                  });
                }

                if (typeof result.starting_inventory === "number") {
                  metricCards.push({
                    key: "starting_inventory",
                    title: "Starting Inventory",
                    tone: "gray",
                    content: `${result.starting_inventory.toFixed(1)} units`,
                  });
                }
              }

              const toneStyles: Record<
                "red" | "blue" | "green" | "purple" | "gray",
                string
              > = {
                red: "border border-rose-400/25 bg-rose-500/10 text-rose-100",
                blue: "border border-cyan-400/25 bg-cyan-500/10 text-cyan-100",
                green:
                  "border border-emerald-400/25 bg-emerald-500/10 text-emerald-100",
                purple:
                  "border border-indigo-400/25 bg-indigo-500/10 text-indigo-100",
                gray: "border border-white/10 bg-white/5 text-slate-100",
              };

              return (
                <div
                  key={index}
                  className="rounded-2xl border border-white/10 bg-gradient-to-b from-white/5 via-white/[0.03] to-slate-950/80 p-6 shadow-[0_20px_70px_-30px_rgba(15,23,42,0.7)]"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <h2 className="text-xl font-semibold text-white">
                      {result.product_name || result.product_id}
                    </h2>
                    <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.22em] text-slate-300">
                      <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 font-semibold text-cyan-200">
                        {modeForResult}
                      </span>
                      {result.demand_frequency && (
                        <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-slate-200">
                          {result.demand_frequency}
                        </span>
                      )}
                    </div>
                  </div>
                  <p className="mb-6 mt-2 text-sm text-slate-300">
                    Inventory confidence powered by the same gradient-and-glass
                    look from the landing page.
                  </p>

                  {/* Key Metrics */}
                  {(metricCards.length > 0 || result.peak_season) && (
                    <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
                      {metricCards.map((card) => (
                        <div
                          key={card.key}
                          className={`rounded-xl p-4 backdrop-blur ${toneStyles[card.tone]}`}
                        >
                          <h3 className="text-sm font-semibold">
                            {card.title}
                          </h3>
                          <p className="mt-1 text-sm font-semibold">
                            {card.content}
                          </p>
                        </div>
                      ))}
                      {result.peak_season && (
                        <div className="rounded-xl border border-emerald-400/25 bg-emerald-500/10 p-4 text-emerald-100 backdrop-blur">
                          <h3 className="text-sm font-semibold">Peak Season</h3>
                          <p className="mt-1 text-sm font-semibold">
                            {result.peak_season}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  <AiSummaryCard
                    summary={result.ai_summary}
                    actions={result.ai_actions}
                    risks={result.ai_risks}
                    source={result.ai_source}
                    generatedAt={result.ai_generated_at}
                    featureEnabled={aiSummaryEnabled}
                    skuLabel={
                      result.product_name || result.product_id || "this SKU"
                    }
                  />

                  {/* Insights */}
                  {result.insights && result.insights.length > 0 && (
                    <div className="mb-6">
                      <h3 className="mb-3 text-sm font-semibold text-white">
                        Insights
                      </h3>
                      <div className="space-y-2">
                        {result.insights.map((insight, i) => (
                          <div
                            key={i}
                            className={`rounded-lg border px-3 py-2 ${
                              insight.severity === "critical"
                                ? "border-rose-400/30 bg-rose-500/10 text-rose-50"
                                : insight.severity === "warning"
                                ? "border-amber-300/30 bg-amber-400/10 text-amber-50"
                                : "border-cyan-400/30 bg-cyan-500/10 text-cyan-50"
                            }`}
                          >
                            <p className="text-sm">
                              <span className="font-semibold capitalize">
                                {insight.type}:
                              </span>{" "}
                              {insight.message}
                              {insight.value && (
                                <span className="ml-2 font-mono">
                                  ({insight.value.toFixed(2)})
                                </span>
                              )}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Forecast Points Preview */}
                  {hasForecastPoints ? (
                    <div className="mb-6">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                        <h3 className="text-sm font-semibold text-white">
                          Forecast Preview ({previewLabel})
                        </h3>
                        <div className="flex flex-wrap gap-2">
                          {(["list", "chart"] as const).map((viewMode) => {
                            const isActive = selectedView === viewMode;
                            return (
                              <button
                                key={viewMode}
                                type="button"
                                onClick={() =>
                                  setForecastViewSelections((prev) => ({
                                    ...prev,
                                    [resultKey]: viewMode,
                                  }))
                                }
                                className={`rounded-full px-3 py-1 text-sm capitalize transition ${
                                  isActive
                                    ? "border border-cyan-400/60 bg-cyan-400/20 text-cyan-50 shadow-[0_10px_30px_-18px_rgba(34,211,238,0.7)]"
                                    : "border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"
                                }`}
                              >
                                {viewMode}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                      <div className="mt-3 flex flex-col gap-3">
                        <div className="flex flex-wrap gap-2">
                          {FORECAST_RANGE_OPTIONS.map(({ label, value }) => {
                            const isActive = value === selectedRange;
                            return (
                              <button
                                key={value}
                                type="button"
                                onClick={() =>
                                  setForecastRangeSelections((prev) => ({
                                    ...prev,
                                    [resultKey]: value,
                                  }))
                                }
                                className={`rounded-full px-3 py-1 text-sm transition ${
                                  isActive
                                    ? "border border-cyan-400/60 bg-cyan-400/20 text-cyan-50 shadow-[0_10px_30px_-18px_rgba(34,211,238,0.7)]"
                                    : "border border-white/10 bg-white/5 text-slate-200 hover:bg-white/10"
                                }`}
                              >
                                {label}
                              </button>
                            );
                          })}
                        </div>
                        {selectedView === "list" ? (
                          <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900/60 shadow-inner">
                            <table className="min-w-full text-sm">
                              <thead>
                                <tr className="border-b border-white/10 text-left text-xs uppercase tracking-wide text-slate-300">
                                  <th className="px-3 py-3">Date</th>
                                  <th className="px-3 py-3">Forecast</th>
                                  <th className="px-3 py-3">Lower Bound</th>
                                  <th className="px-3 py-3">Upper Bound</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-white/5 text-slate-100">
                                {forecastPointsToShow.map((point, i) => (
                                  <tr key={i} className="hover:bg-white/5">
                                    <td className="px-3 py-2">{point.date}</td>
                                    <td className="px-3 py-2 font-mono">
                                      {point.forecast?.toFixed(1) || "0.0"}
                                    </td>
                                    <td className="px-3 py-2 font-mono">
                                      {point.lower_bound
                                        ? point.lower_bound.toFixed(1)
                                        : "-"}
                                    </td>
                                    <td className="px-3 py-2 font-mono">
                                      {point.upper_bound
                                        ? point.upper_bound.toFixed(1)
                                        : "-"}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <div className="h-72 w-full rounded-xl border border-white/10 bg-slate-900/60 p-2">
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart
                                data={chartData}
                                margin={{
                                  top: 16,
                                  right: 24,
                                  left: 8,
                                  bottom: 8,
                                }}
                              >
                                <CartesianGrid
                                  strokeDasharray="3 3"
                                  stroke="rgba(148, 163, 184, 0.2)"
                                />
                                <XAxis
                                  dataKey="date"
                                  tick={{ fill: "#cbd5e1", fontSize: 12 }}
                                  tickLine={{ stroke: "rgba(148,163,184,0.4)" }}
                                  axisLine={{ stroke: "rgba(148,163,184,0.4)" }}
                                />
                                <YAxis
                                  tick={{ fill: "#cbd5e1", fontSize: 12 }}
                                  tickLine={{ stroke: "rgba(148,163,184,0.4)" }}
                                  axisLine={{ stroke: "rgba(148,163,184,0.4)" }}
                                />
                                <Tooltip
                                  contentStyle={{
                                    backgroundColor: "#0f172a",
                                    border: "1px solid rgba(148, 163, 184, 0.4)",
                                    borderRadius: "12px",
                                    color: "#e2e8f0",
                                  }}
                                  labelStyle={{ color: "#cbd5e1" }}
                                  formatter={(value) =>
                                    typeof value === "number"
                                      ? value.toFixed(1)
                                      : value ?? "-"
                                  }
                                />
                                <Legend />
                                <Line
                                  type="monotone"
                                  dataKey="forecast"
                                  name="Forecast"
                                  stroke="#22d3ee"
                                  strokeWidth={2}
                                  dot={false}
                                  connectNulls
                                />
                                <Line
                                  type="monotone"
                                  dataKey="lower"
                                  name="Lower Bound"
                                  stroke="#34d399"
                                  strokeDasharray="5 5"
                                  strokeWidth={1.8}
                                  dot={false}
                                  connectNulls
                                />
                                <Line
                                  type="monotone"
                                  dataKey="upper"
                                  name="Upper Bound"
                                  stroke="#fbbf24"
                                  strokeDasharray="5 5"
                                  strokeWidth={1.8}
                                  dot={false}
                                  connectNulls
                                />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="mb-6 rounded-xl border border-amber-300/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
                      ⚠️ No forecast points available. The forecast may still be
                      processing or encountered an error.
                    </div>
                  )}

                  {/* Accuracy Metrics */}
                  {result.accuracy_metrics && (
                    <div className="mb-6">
                      <h3 className="mb-3 text-sm font-semibold text-white">
                        Model Accuracy
                      </h3>
                      <div className="grid grid-cols-2 gap-4 md:grid-cols-3 lg:grid-cols-6">
                        <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                          <p className="text-[11px] uppercase tracking-wide text-slate-300">
                            MAE
                          </p>
                          <p className="font-mono text-sm text-white">
                            {result.accuracy_metrics?.MAE?.toFixed(2) ?? "-"}
                          </p>
                          <p className="mt-1 text-[11px] text-slate-400">
                            Avg absolute units off (lower is better)
                          </p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                          <p className="text-[11px] uppercase tracking-wide text-slate-300">
                            RMSE
                          </p>
                          <p className="font-mono text-sm text-white">
                            {result.accuracy_metrics?.RMSE?.toFixed(2) ?? "-"}
                          </p>
                          <p className="mt-1 text-[11px] text-slate-400">
                            Penalizes big misses more than MAE
                          </p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                          <p className="text-[11px] uppercase tracking-wide text-slate-300">
                            MAPE
                          </p>
                          <p className="font-mono text-sm text-white">
                            {result.accuracy_metrics?.MAPE?.toFixed(1)}%
                          </p>
                          <p className="mt-1 text-[11px] text-slate-400">
                            Avg percent error where actual ≠ 0
                          </p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                          <p className="text-[11px] uppercase tracking-wide text-slate-300">
                            WAPE
                          </p>
                          <p className="font-mono text-sm text-white">
                            {result.accuracy_metrics?.WAPE?.toFixed(1)}%
                          </p>
                          <p className="mt-1 text-[11px] text-slate-400">
                            Weighted avg percent error (stable even with zeros)
                          </p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                          <p className="text-[11px] uppercase tracking-wide text-slate-300">
                            sMAPE
                          </p>
                          <p className="font-mono text-sm text-white">
                            {result.accuracy_metrics?.sMAPE?.toFixed(1)}%
                          </p>
                          <p className="mt-1 text-[11px] text-slate-400">
                            Symmetric percent error; balances over/under
                          </p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 p-3 text-center">
                          <p className="text-[11px] uppercase tracking-wide text-slate-300">
                            Model
                          </p>
                          <p className="text-sm text-white">
                            {result.model_used}
                          </p>
                          <p className="mt-1 text-[11px] text-slate-400">
                            Algorithm used for this SKU
                          </p>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* External Factors Analysis */}
                  {result.external_factors_used &&
                    result.external_factors_used.length > 0 && (
                      <div className="mb-6">
                        <h3 className="mb-3 text-sm font-semibold text-white">
                          External Factors Used
                        </h3>
                        <div className="flex flex-wrap gap-2">
                          {result.external_factors_used.map((factor, i) => (
                            <span
                              key={i}
                              className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs uppercase tracking-wide text-slate-200"
                            >
                              {factor}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* External Factors Analysis */}
                  {result.external_factors && (
                    <div className="mb-6">
                      <ExternalFactors
                        weatherData={result.external_factors.weather_data}
                        holidayData={result.external_factors.holiday_data}
                        factorAttributions={
                          result.external_factors.factor_attributions
                        }
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : jobData.status === "FAILED" ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-rose-100">
            Forecast generation failed. Please try again with a different file.
          </div>
        ) : (
          <div className="py-10 text-center">
            <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-b-2 border-cyan-400"></div>
            <p className="text-slate-300">
              {jobData.status === "PROCESSING"
                ? "Generating forecast..."
                : "Forecast in queue..."}
            </p>
          </div>
        )}
      </div>
    </main>
  );
}

export default function ResultsPage() {
  return (
    <Suspense fallback={<Loading />}>
      <ResultsPageContent />
    </Suspense>
  );
}
