"use client";

import { useEffect, useState } from "react";
import { getForecastResult, ForecastResult } from "@/services/api";
import { useSearchParams } from "next/navigation";
import { ExternalFactors } from "@/components/Results/ExternalFactors";
import { AIAnalysisComponent } from "@/components/Results/AIAnalysis";
import { Loading } from "@/components/Results/Loading";
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

export default function ResultsPage() {
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

    useEffect(() => {
        if (!jobId) return;

        const interval = setInterval(async () => {
            try {
                const response = await getForecastResult(jobId);
                console.log("🔍 Forecast Response:", response); // Debug logging
                setJobData(response);

                if (
                    response.status === "COMPLETED" ||
                    response.status === "FAILED"
                ) {
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
            <div className="p-6">
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                    <p className="text-red-800">{error}</p>
                </div>
            </div>
        );
    }

    if (!jobData) {
        return <Loading />;
    }

    return (
        <div className="p-6 max-w-6xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">Forecast Results</h1>

            {/* Job Status */}
            <div className="mb-6">
                <div
                    className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${
                        jobData.status === "COMPLETED"
                            ? "bg-green-100 text-green-800"
                            : jobData.status === "FAILED"
                            ? "bg-red-100 text-red-800"
                            : jobData.status === "PROCESSING"
                            ? "bg-blue-100 text-blue-800"
                            : "bg-yellow-100 text-yellow-800"
                    }`}
                >
                    {jobData.status}
                </div>
                {jobData.error_message && (
                    <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md">
                        <p className="text-red-800 text-sm">
                            {jobData.error_message}
                        </p>
                    </div>
                )}
            </div>

            {jobData.status === "COMPLETED" && jobData.results ? (
                <div className="space-y-8">
                    {jobData.results.map((result, index) => {
                        const resultKey =
                            result.product_id ??
                            result.product_name ??
                            index.toString();
                        const selectedRange =
                            forecastRangeSelections[resultKey] ?? "7";
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
                                : result.forecast_points.slice(
                                      0,
                                      Number(selectedRange)
                                  )
                            : [];
                        const selectedView =
                            forecastViewSelections[resultKey] ?? "list";
                        const chartData = forecastPointsToShow.map((point) => ({
                            date: point.date,
                            forecast:
                                point.forecast === undefined
                                    ? null
                                    : point.forecast,
                            lower:
                                point.lower_bound === undefined
                                    ? null
                                    : point.lower_bound,
                            upper:
                                point.upper_bound === undefined
                                    ? null
                                    : point.upper_bound,
                        }));
                        const previewLabel =
                            selectedOption.value === "max"
                                ? "All Forecast Points"
                                : `Next ${selectedOption.label}`;

                        return (
                            <div
                                key={index}
                                className="bg-white border rounded-lg p-6 shadow-sm"
                            >
                                <h2 className="text-xl font-semibold mb-4">
                                    {result.product_name || result.product_id}
                                </h2>

                                {/* Key Metrics */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                    {result.stockout_date && (
                                        <div className="bg-red-50 p-4 rounded-md">
                                            <h3 className="font-medium text-red-900">
                                                Stockout Date
                                            </h3>
                                            <p className="text-red-800">
                                                {result.stockout_date}
                                            </p>
                                        </div>
                                    )}
                                    {result.reorder_point && (
                                        <div className="bg-blue-50 p-4 rounded-md">
                                            <h3 className="font-medium text-blue-900">
                                                Reorder Point
                                            </h3>
                                            <p className="text-blue-800">
                                                {result.reorder_point.toFixed(
                                                    1
                                                )}{" "}
                                                units
                                            </p>
                                        </div>
                                    )}
                                    {result.peak_season && (
                                        <div className="bg-green-50 p-4 rounded-md">
                                            <h3 className="font-medium text-green-900">
                                                Peak Season
                                            </h3>
                                            <p className="text-green-800">
                                                {result.peak_season}
                                            </p>
                                        </div>
                                    )}
                                </div>

                                {/* Insights */}
                                {result.insights &&
                                    result.insights.length > 0 && (
                                        <div className="mb-6">
                                            <h3 className="font-medium mb-3">
                                                Insights
                                            </h3>
                                            <div className="space-y-2">
                                                {result.insights.map(
                                                    (insight, i) => (
                                                        <div
                                                            key={i}
                                                            className={`p-3 rounded-md ${
                                                                insight.severity ===
                                                                "critical"
                                                                    ? "bg-red-50 border border-red-200"
                                                                    : insight.severity ===
                                                                      "warning"
                                                                    ? "bg-yellow-50 border border-yellow-200"
                                                                    : "bg-blue-50 border border-blue-200"
                                                            }`}
                                                        >
                                                            <p
                                                                className={`text-sm ${
                                                                    insight.severity ===
                                                                    "critical"
                                                                        ? "text-red-800"
                                                                        : insight.severity ===
                                                                          "warning"
                                                                        ? "text-yellow-800"
                                                                        : "text-blue-800"
                                                                }`}
                                                            >
                                                                <span className="font-medium capitalize">
                                                                    {
                                                                        insight.type
                                                                    }
                                                                    :
                                                                </span>{" "}
                                                                {
                                                                    insight.message
                                                                }
                                                                {insight.value && (
                                                                    <span className="ml-2 font-mono">
                                                                        (
                                                                        {insight.value.toFixed(
                                                                            2
                                                                        )}
                                                                        )
                                                                    </span>
                                                                )}
                                                            </p>
                                                        </div>
                                                    )
                                                )}
                                            </div>
                                        </div>
                                    )}

                                {/* Forecast Points Preview */}
                                {hasForecastPoints ? (
                                    <div className="mb-6">
                                        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                                            <h3 className="font-medium">
                                                Forecast Preview ({previewLabel})
                                            </h3>
                                            <div className="flex flex-wrap gap-2">
                                                {(["list", "chart"] as const).map(
                                                    (viewMode) => {
                                                        const isActive =
                                                            selectedView ===
                                                            viewMode;
                                                        return (
                                                            <button
                                                                key={viewMode}
                                                                type="button"
                                                                onClick={() =>
                                                                    setForecastViewSelections(
                                                                        (
                                                                            prev
                                                                        ) => ({
                                                                            ...prev,
                                                                            [resultKey]:
                                                                                viewMode,
                                                                        })
                                                                    )
                                                                }
                                                                className={`px-3 py-1 rounded-full text-sm border transition capitalize ${
                                                                    isActive
                                                                        ? "bg-slate-900 text-white border-slate-900"
                                                                        : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                                                                }`}
                                                            >
                                                                {viewMode}
                                                            </button>
                                                        );
                                                    }
                                                )}
                                            </div>
                                        </div>
                                        <div className="mt-3 flex flex-col gap-3">
                                            <div className="flex flex-wrap gap-2">
                                                {FORECAST_RANGE_OPTIONS.map(
                                                    ({ label, value }) => {
                                                        const isActive =
                                                            value ===
                                                            selectedRange;
                                                        return (
                                                            <button
                                                                key={value}
                                                                type="button"
                                                                onClick={() =>
                                                                    setForecastRangeSelections(
                                                                        (
                                                                            prev
                                                                        ) => ({
                                                                            ...prev,
                                                                            [resultKey]:
                                                                                value,
                                                                        })
                                                                    )
                                                                }
                                                                className={`px-3 py-1 rounded-full text-sm border transition ${
                                                                    isActive
                                                                        ? "bg-blue-600 text-white border-blue-600"
                                                                        : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                                                                }`}
                                                            >
                                                                {label}
                                                            </button>
                                                        );
                                                    }
                                                )}
                                            </div>
                                            {selectedView === "list" ? (
                                                <div className="overflow-x-auto">
                                                    <table className="min-w-full text-sm">
                                                        <thead>
                                                            <tr className="border-b">
                                                                <th className="text-left py-2">
                                                                    Date
                                                                </th>
                                                                <th className="text-left py-2">
                                                                    Forecast
                                                                </th>
                                                                <th className="text-left py-2">
                                                                    Lower Bound
                                                                </th>
                                                                <th className="text-left py-2">
                                                                    Upper Bound
                                                                </th>
                                                            </tr>
                                                        </thead>
                                                        <tbody>
                                                            {forecastPointsToShow.map(
                                                                (point, i) => (
                                                                    <tr
                                                                        key={i}
                                                                        className="border-b"
                                                                    >
                                                                        <td className="py-2">
                                                                            {
                                                                                point.date
                                                                            }
                                                                        </td>
                                                                        <td className="py-2 font-mono">
                                                                            {point.forecast?.toFixed(
                                                                                1
                                                                            ) ||
                                                                                "0.0"}
                                                                        </td>
                                                                        <td className="py-2 font-mono">
                                                                            {point.lower_bound
                                                                                ? point.lower_bound.toFixed(
                                                                                      1
                                                                                  )
                                                                                : "-"}
                                                                        </td>
                                                                        <td className="py-2 font-mono">
                                                                            {point.upper_bound
                                                                                ? point.upper_bound.toFixed(
                                                                                      1
                                                                                  )
                                                                                : "-"}
                                                                        </td>
                                                                    </tr>
                                                                )
                                                            )}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            ) : (
                                                <div className="h-72 w-full">
                                                    <ResponsiveContainer
                                                        width="100%"
                                                        height="100%"
                                                    >
                                                        <LineChart
                                                            data={chartData}
                                                            margin={{
                                                                top: 16,
                                                                right: 24,
                                                                left: 8,
                                                                bottom: 8,
                                                            }}
                                                        >
                                                            <CartesianGrid strokeDasharray="3 3" />
                                                            <XAxis dataKey="date" />
                                                            <YAxis />
                                                            <Tooltip
                                                                formatter={(
                                                                    value
                                                                ) =>
                                                                    typeof value ===
                                                                        "number"
                                                                        ? value.toFixed(
                                                                              1
                                                                          )
                                                                        : value ?? "-"
                                                                }
                                                            />
                                                            <Legend />
                                                            <Line
                                                                type="monotone"
                                                                dataKey="forecast"
                                                                name="Forecast"
                                                                stroke="#2563eb"
                                                                strokeWidth={2}
                                                                dot={false}
                                                                connectNulls
                                                            />
                                                            <Line
                                                                type="monotone"
                                                                dataKey="lower"
                                                                name="Lower Bound"
                                                                stroke="#10b981"
                                                                strokeDasharray="5 5"
                                                                strokeWidth={1.5}
                                                                dot={false}
                                                                connectNulls
                                                            />
                                                            <Line
                                                                type="monotone"
                                                                dataKey="upper"
                                                                name="Upper Bound"
                                                                stroke="#f97316"
                                                                strokeDasharray="5 5"
                                                                strokeWidth={1.5}
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
                                    <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
                                        <p className="text-yellow-800 text-sm">
                                            ⚠️ No forecast points available. The
                                            forecast may still be processing or
                                            encountered an error.
                                        </p>
                                    </div>
                                )}

                                {/* Accuracy Metrics */}
                                {result.accuracy_metrics && (
                                    <div className="mb-6">
                                        <h3 className="font-medium mb-3">
                                            Model Accuracy
                                        </h3>
                                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                            <div className="text-center p-3 bg-gray-50 rounded-md">
                                                <p className="text-xs text-gray-600">
                                                    MAE
                                                </p>
                                                <p className="font-mono text-sm">
                                                    {result.accuracy_metrics.MAE.toFixed(
                                                        2
                                                    )}
                                                </p>
                                            </div>
                                            <div className="text-center p-3 bg-gray-50 rounded-md">
                                                <p className="text-xs text-gray-600">
                                                    RMSE
                                                </p>
                                                <p className="font-mono text-sm">
                                                    {result.accuracy_metrics.RMSE.toFixed(
                                                        2
                                                    )}
                                                </p>
                                            </div>
                                            <div className="text-center p-3 bg-gray-50 rounded-md">
                                                <p className="text-xs text-gray-600">
                                                    MAPE
                                                </p>
                                                <p className="font-mono text-sm">
                                                    {result.accuracy_metrics.MAPE.toFixed(
                                                        1
                                                    )}
                                                    %
                                                </p>
                                            </div>
                                            <div className="text-center p-3 bg-gray-50 rounded-md">
                                                <p className="text-xs text-gray-600">
                                                    Model
                                                </p>
                                                <p className="text-sm">
                                                    {result.model_used}
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                )}

                                {/* External Factors Analysis */}
                                {result.external_factors_used &&
                                    result.external_factors_used.length > 0 && (
                                        <div className="mb-6">
                                            <h3 className="font-medium mb-3">
                                                External Factors Used
                                            </h3>
                                            <div className="flex flex-wrap gap-2">
                                                {result.external_factors_used.map(
                                                    (factor, i) => (
                                                        <span
                                                            key={i}
                                                            className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm"
                                                        >
                                                            {factor}
                                                        </span>
                                                    )
                                                )}
                                            </div>
                                        </div>
                                    )}

                                {/* AI Analysis Section */}
                                {(result.ai_trend_explanation ||
                                    result.ai_factor_summary ||
                                    result.ai_recommendations ||
                                    result.ai_risk_assessment) && (
                                    <div className="mb-6">
                                        <h3 className="font-medium mb-3">
                                            AI Analysis
                                        </h3>
                                        <div className="space-y-4">
                                            {result.ai_trend_explanation && (
                                                <div className="bg-blue-50 p-4 rounded-md">
                                                    <h4 className="font-medium text-blue-900 mb-2">
                                                        Trend Explanation
                                                    </h4>
                                                    <p className="text-blue-800 text-sm">
                                                        {
                                                            result.ai_trend_explanation
                                                        }
                                                    </p>
                                                </div>
                                            )}
                                            {result.ai_factor_summary && (
                                                <div className="bg-green-50 p-4 rounded-md">
                                                    <h4 className="font-medium text-green-900 mb-2">
                                                        Factor Summary
                                                    </h4>
                                                    <p className="text-green-800 text-sm">
                                                        {
                                                            result.ai_factor_summary
                                                        }
                                                    </p>
                                                </div>
                                            )}
                                            {result.ai_recommendations &&
                                                result.ai_recommendations
                                                    .length > 0 && (
                                                    <div className="bg-purple-50 p-4 rounded-md">
                                                        <h4 className="font-medium text-purple-900 mb-2">
                                                            AI Recommendations
                                                        </h4>
                                                        <ul className="text-purple-800 text-sm space-y-1">
                                                            {result.ai_recommendations.map(
                                                                (rec, i) => (
                                                                    <li
                                                                        key={i}
                                                                        className="flex items-start"
                                                                    >
                                                                        <span className="mr-2">
                                                                            •
                                                                        </span>
                                                                        <span>
                                                                            {
                                                                                rec
                                                                            }
                                                                        </span>
                                                                    </li>
                                                                )
                                                            )}
                                                        </ul>
                                                    </div>
                                                )}
                                            {result.ai_risk_assessment && (
                                                <div className="bg-yellow-50 p-4 rounded-md">
                                                    <h4 className="font-medium text-yellow-900 mb-2">
                                                        Risk Assessment
                                                    </h4>
                                                    <p className="text-yellow-800 text-sm">
                                                        {
                                                            result.ai_risk_assessment
                                                        }
                                                    </p>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* Legacy AI Analysis (fallback) */}
                                {result.ai_analysis && (
                                    <div className="mb-6">
                                        <AIAnalysisComponent
                                            analysis={result.ai_analysis}
                                            dataQualityScore={
                                                result.data_quality_score
                                            }
                                        />
                                    </div>
                                )}

                                {/* External Factors Analysis */}
                                {result.external_factors && (
                                    <div className="mb-6">
                                        <ExternalFactors
                                            weatherData={
                                                result.external_factors
                                                    .weather_data
                                            }
                                            holidayData={
                                                result.external_factors
                                                    .holiday_data
                                            }
                                            factorAttributions={
                                                result.external_factors
                                                    .factor_attributions
                                            }
                                        />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            ) : jobData.status === "FAILED" ? (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                    <p className="text-red-800">
                        Forecast generation failed. Please try again with a
                        different file.
                    </p>
                </div>
            ) : (
                <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">
                        {jobData.status === "PROCESSING"
                            ? "Generating forecast..."
                            : "Forecast in queue..."}
                    </p>
                </div>
            )}
        </div>
    );
}
