"use client";

import { useEffect, useState } from "react";
import { getForecastResult } from "@/services/api";
import { useSearchParams } from "next/navigation";

export default function ResultsPage() {
    const searchParams = useSearchParams();
    const jobId = searchParams.get("jobId");
    const [status, setStatus] = useState("PENDING");
    const [result, setResult] = useState<any>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!jobId) return;

        const interval = setInterval(async () => {
            try {
                const response = await getForecastResult(jobId);
                setStatus(response.status);
                if (response.status === "COMPLETED") {
                    setResult(response.results);
                    clearInterval(interval);
                }
            } catch (err: any) {
                setError("Failed to fetch forecast result");
                clearInterval(interval);
            }
        }, 2000);

        return () => clearInterval(interval);
    }, [jobId]);

    if (error) return <div className="text-red-600">{error}</div>;

    return (
        <div className="p-6">
            <h1 className="text-xl font-bold mb-4">Forecast Results</h1>
            {status === "COMPLETED" && result ? (
                <div className="space-y-4">
                    <p>
                        <strong>Stockout Date:</strong> {result.stockoutDate}
                    </p>
                    <p>
                        <strong>Reorder Point:</strong> {result.reorderPoint}
                    </p>
                    <p>
                        <strong>Peak Season:</strong> {result.peakSeason}
                    </p>
                    <div>
                        <strong>Insights:</strong>
                        <ul className="list-disc pl-6">
                            {result.insights.map(
                                (insight: string, index: number) => (
                                    <li key={index}>{insight}</li>
                                )
                            )}
                        </ul>
                    </div>
                </div>
            ) : (
                <p>Forecast in progress... Please wait.</p>
            )}
        </div>
    );
}
