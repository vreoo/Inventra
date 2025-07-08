"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

export default function ResultsPage() {
    const searchParams = useSearchParams();
    const jobId = searchParams.get("jobId") || "unknown";

    const [status, setStatus] = useState("PENDING");
    const [chartReady, setChartReady] = useState(false);
    const [insights, setInsights] = useState<any>(null);

    const data = [
        { date: "2024-01-01", forecast: 120 },
        { date: "2024-01-02", forecast: 44 },
        { date: "2024-01-03", forecast: 78 },
        { date: "2024-01-04", forecast: 99 },
        { date: "2024-01-05", forecast: 150 },
        { date: "2024-01-06", forecast: 130 },
        { date: "2024-01-07", forecast: 170 },
        { date: "2024-01-08", forecast: 200 },
        { date: "2024-01-09", forecast: 180 },
        { date: "2024-01-10", forecast: 220 },
    ];

    useEffect(() => {
        const interval = setInterval(() => {
            setStatus((prev) => {
                if (prev === "PENDING") return "PROCESSING";
                if (prev === "PROCESSING") {
                    clearInterval(interval);
                    setChartReady(true);
                    setInsights({
                        stockoutDate: "2025-08-10",
                        reorderPoint: 42,
                        peakSeason: "November - December",
                    });
                    return "COMPLETED";
                }
                return prev;
            });
        }, 2000);

        return () => clearInterval(interval);
    }, []);

    return (
        <main className="p-8 max-w-5xl mx-auto space-y-8">
            <h1 className="text-2xl font-bold">Forecast Results</h1>

            <Card>
                <CardContent className="p-6 space-y-4">
                    <div className="font-mono text-sm">Job ID: {jobId}</div>
                    <div>Status: {status}</div>
                </CardContent>
            </Card>

            {chartReady ? (
                <Card>
                    <CardContent className="p-6">
                        <h2 className="text-xl font-semibold mb-4">
                            Forecast Chart
                        </h2>
                        <div className="h-64 bg-muted rounded-xl flex items-center justify-center text-muted-foreground">
                            <ResponsiveContainer width="100%" height={300}>
                                <LineChart data={data}>
                                    <XAxis dataKey="date" />
                                    <YAxis />
                                    <Tooltip />
                                    <Line
                                        type="monotone"
                                        dataKey="forecast"
                                        stroke="#3b82f6"
                                        strokeWidth={2}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                    </CardContent>
                </Card>
            ) : (
                <Skeleton className="h-64 w-full rounded-xl" />
            )}

            {insights && (
                <Card>
                    <CardContent className="p-6 space-y-4">
                        <h2 className="text-xl font-semibold">Insights</h2>
                        <ul className="list-disc pl-6 text-sm space-y-1">
                            <li>
                                <strong>Predicted Stockout Date:</strong>{" "}
                                {insights.stockoutDate}
                            </li>
                            <li>
                                <strong>Reorder Point:</strong>{" "}
                                {insights.reorderPoint}
                            </li>
                            <li>
                                <strong>Peak Season:</strong>{" "}
                                {insights.peakSeason}
                            </li>
                        </ul>
                        <Button
                            variant="outline"
                            className="mt-4"
                            onClick={() => alert("CSV Exported!")}
                        >
                            Export CSV Report
                        </Button>
                    </CardContent>
                </Card>
            )}
        </main>
    );
}
