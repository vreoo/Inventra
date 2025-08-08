"use client";

import { useEffect, useState } from "react";
import { getForecastResult, ForecastResult } from "@/services/api";
import { useSearchParams } from "next/navigation";

export default function ResultsPage() {
    const searchParams = useSearchParams();
    const jobId = searchParams.get("jobId");
    const [jobData, setJobData] = useState<ForecastResult | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!jobId) return;

        const interval = setInterval(async () => {
            try {
                const response = await getForecastResult(jobId);
                setJobData(response);
                
                if (response.status === "COMPLETED" || response.status === "FAILED") {
                    clearInterval(interval);
                }
            } catch (err: any) {
                setError("Failed to fetch forecast result");
                clearInterval(interval);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [jobId]);

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
        return (
            <div className="p-6">
                <h1 className="text-xl font-bold mb-4">Forecast Results</h1>
                <p>Loading...</p>
            </div>
        );
    }

    return (
        <div className="p-6 max-w-6xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">Forecast Results</h1>
            
            {/* Job Status */}
            <div className="mb-6">
                <div className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${
                    jobData.status === "COMPLETED" ? "bg-green-100 text-green-800" :
                    jobData.status === "FAILED" ? "bg-red-100 text-red-800" :
                    jobData.status === "PROCESSING" ? "bg-blue-100 text-blue-800" :
                    "bg-yellow-100 text-yellow-800"
                }`}>
                    {jobData.status}
                </div>
                {jobData.error_message && (
                    <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded-md">
                        <p className="text-red-800 text-sm">{jobData.error_message}</p>
                    </div>
                )}
            </div>

            {jobData.status === "COMPLETED" && jobData.results ? (
                <div className="space-y-8">
                    {jobData.results.map((result, index) => (
                        <div key={index} className="bg-white border rounded-lg p-6 shadow-sm">
                            <h2 className="text-xl font-semibold mb-4">
                                {result.product_name || result.product_id}
                            </h2>
                            
                            {/* Key Metrics */}
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                                {result.stockout_date && (
                                    <div className="bg-red-50 p-4 rounded-md">
                                        <h3 className="font-medium text-red-900">Stockout Date</h3>
                                        <p className="text-red-800">{result.stockout_date}</p>
                                    </div>
                                )}
                                {result.reorder_point && (
                                    <div className="bg-blue-50 p-4 rounded-md">
                                        <h3 className="font-medium text-blue-900">Reorder Point</h3>
                                        <p className="text-blue-800">{result.reorder_point.toFixed(1)} units</p>
                                    </div>
                                )}
                                {result.peak_season && (
                                    <div className="bg-green-50 p-4 rounded-md">
                                        <h3 className="font-medium text-green-900">Peak Season</h3>
                                        <p className="text-green-800">{result.peak_season}</p>
                                    </div>
                                )}
                            </div>

                            {/* Insights */}
                            {result.insights && result.insights.length > 0 && (
                                <div className="mb-6">
                                    <h3 className="font-medium mb-3">Insights</h3>
                                    <div className="space-y-2">
                                        {result.insights.map((insight, i) => (
                                            <div key={i} className={`p-3 rounded-md ${
                                                insight.severity === "critical" ? "bg-red-50 border border-red-200" :
                                                insight.severity === "warning" ? "bg-yellow-50 border border-yellow-200" :
                                                "bg-blue-50 border border-blue-200"
                                            }`}>
                                                <p className={`text-sm ${
                                                    insight.severity === "critical" ? "text-red-800" :
                                                    insight.severity === "warning" ? "text-yellow-800" :
                                                    "text-blue-800"
                                                }`}>
                                                    <span className="font-medium capitalize">{insight.type}:</span> {insight.message}
                                                    {insight.value && (
                                                        <span className="ml-2 font-mono">({insight.value.toFixed(2)})</span>
                                                    )}
                                                </p>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Forecast Points Preview */}
                            {result.forecast_points && result.forecast_points.length > 0 && (
                                <div className="mb-6">
                                    <h3 className="font-medium mb-3">Forecast Preview (Next 7 Days)</h3>
                                    <div className="overflow-x-auto">
                                        <table className="min-w-full text-sm">
                                            <thead>
                                                <tr className="border-b">
                                                    <th className="text-left py-2">Date</th>
                                                    <th className="text-left py-2">Forecast</th>
                                                    <th className="text-left py-2">Lower Bound</th>
                                                    <th className="text-left py-2">Upper Bound</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {result.forecast_points.slice(0, 7).map((point, i) => (
                                                    <tr key={i} className="border-b">
                                                        <td className="py-2">{point.date}</td>
                                                        <td className="py-2 font-mono">{point.forecast.toFixed(1)}</td>
                                                        <td className="py-2 font-mono">
                                                            {point.lower_bound ? point.lower_bound.toFixed(1) : "-"}
                                                        </td>
                                                        <td className="py-2 font-mono">
                                                            {point.upper_bound ? point.upper_bound.toFixed(1) : "-"}
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>
                            )}

                            {/* Accuracy Metrics */}
                            {result.accuracy_metrics && (
                                <div>
                                    <h3 className="font-medium mb-3">Model Accuracy</h3>
                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                        <div className="text-center p-3 bg-gray-50 rounded-md">
                                            <p className="text-xs text-gray-600">MAE</p>
                                            <p className="font-mono text-sm">{result.accuracy_metrics.MAE.toFixed(2)}</p>
                                        </div>
                                        <div className="text-center p-3 bg-gray-50 rounded-md">
                                            <p className="text-xs text-gray-600">RMSE</p>
                                            <p className="font-mono text-sm">{result.accuracy_metrics.RMSE.toFixed(2)}</p>
                                        </div>
                                        <div className="text-center p-3 bg-gray-50 rounded-md">
                                            <p className="text-xs text-gray-600">MAPE</p>
                                            <p className="font-mono text-sm">{result.accuracy_metrics.MAPE.toFixed(1)}%</p>
                                        </div>
                                        <div className="text-center p-3 bg-gray-50 rounded-md">
                                            <p className="text-xs text-gray-600">Model</p>
                                            <p className="text-sm">{result.model_used}</p>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            ) : jobData.status === "FAILED" ? (
                <div className="bg-red-50 border border-red-200 rounded-md p-4">
                    <p className="text-red-800">Forecast generation failed. Please try again with a different file.</p>
                </div>
            ) : (
                <div className="text-center py-8">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                    <p className="text-gray-600">
                        {jobData.status === "PROCESSING" ? "Generating forecast..." : "Forecast in queue..."}
                    </p>
                </div>
            )}
        </div>
    );
}
