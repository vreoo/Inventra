// src/api/forecast.ts

// This is a placeholder service to simulate API integration.
// Replace this with real fetch logic when backend is ready.

// Simulated forecast result data
const mockForecastData = [
    { date: "2024-01-01", forecast: 120 },
    { date: "2024-01-02", forecast: 135 },
    { date: "2024-01-03", forecast: 150 },
    { date: "2024-01-04", forecast: 170 },
    { date: "2024-01-05", forecast: 160 },
    { date: "2024-01-06", forecast: 175 },
    { date: "2024-01-07", forecast: 190 },
];

let simulatedStatus = "PENDING";
let checkCount = 0;

export async function fetchForecastStatus(
    jobId: string
): Promise<"PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"> {
    console.log("Checking status for jobId:", jobId);
    await new Promise((r) => setTimeout(r, 800));
    checkCount++;
    if (checkCount < 3) return "PENDING";
    if (checkCount < 5) return "PROCESSING";
    return "COMPLETED";
}

export async function fetchForecastResults(jobId: string): Promise<any[]> {
    console.log("Fetching results for jobId:", jobId);
    await new Promise((r) => setTimeout(r, 1000));
    return mockForecastData;
}
