const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "localhost:3000";

export async function uploadFile(
    formData: FormData
): Promise<{ fileId: string }> {
    const res = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
    });
    if (!res.ok) throw new Error("Failed to upload file");
    return res.json();
}

export async function createForecastJob(
    fileId: string,
    config: Record<string, any>
): Promise<{ jobId: string }> {
    const res = await fetch(`${API_BASE_URL}/forecast`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fileId, config }),
    });
    if (!res.ok) throw new Error("Failed to create forecast job");
    return res.json();
}

export async function getForecastResult(jobId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/forecast/${jobId}`);
    if (!res.ok) throw new Error("Failed to fetch forecast result");
    return res.json();
}
