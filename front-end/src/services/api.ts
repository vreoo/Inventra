const API_BASE_URL = typeof window !== 'undefined' 
    ? (window as any).ENV?.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api"
    : "http://localhost:8000/api";

export interface ForecastConfig {
    model?: "AutoARIMA" | "AutoETS" | "SeasonalNaive" | "Naive" | "RandomWalkWithDrift";
    horizon?: number;
    frequency?: string;
    confidence_level?: number;
    seasonal_length?: number | null;
}

export interface UploadResponse {
    fileId: string;
    filename: string;
    validation: {
        valid: boolean;
        errors: string[];
        warnings: string[];
        info: {
            rows: number;
            columns: string[];
            date_columns: string[];
            numeric_columns: string[];
            text_columns: string[];
        };
    };
}

export interface ForecastJobResponse {
    jobId: string;
}

export interface ForecastResult {
    jobId: string;
    fileId: string;
    status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
    created_at: string;
    completed_at?: string;
    error_message?: string;
    results?: Array<{
        product_id: string;
        product_name?: string;
        model_used: string;
        forecast_points: Array<{
            date: string;
            forecast: number;
            lower_bound?: number;
            upper_bound?: number;
        }>;
        stockout_date?: string;
        reorder_point?: number;
        reorder_date?: string;
        peak_season?: string;
        insights: Array<{
            type: string;
            message: string;
            severity: string;
            value?: number;
        }>;
        accuracy_metrics?: {
            MAE: number;
            MSE: number;
            RMSE: number;
            MAPE: number;
        };
    }>;
    config?: ForecastConfig;
}

export async function uploadFile(formData: FormData): Promise<UploadResponse> {
    const res = await fetch(`${API_BASE_URL}/upload`, {
        method: "POST",
        body: formData,
    });
    
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Failed to upload file" }));
        throw new Error(errorData.detail || "Failed to upload file");
    }
    
    return res.json();
}

export async function createForecastJob(
    fileId: string,
    config: ForecastConfig = {}
): Promise<ForecastJobResponse> {
    const defaultConfig: ForecastConfig = {
        model: "AutoARIMA",
        horizon: 30,
        frequency: "D",
        confidence_level: 0.95,
        ...config
    };

    const res = await fetch(`${API_BASE_URL}/forecast`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fileId, config: defaultConfig }),
    });
    
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Failed to create forecast job" }));
        throw new Error(errorData.detail || "Failed to create forecast job");
    }
    
    return res.json();
}

export async function getForecastResult(jobId: string): Promise<ForecastResult> {
    const res = await fetch(`${API_BASE_URL}/forecast/${jobId}`);
    
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Failed to fetch forecast result" }));
        throw new Error(errorData.detail || "Failed to fetch forecast result");
    }
    
    return res.json();
}

export async function validateFile(fileId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/upload/${fileId}/validate`);
    
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: "Failed to validate file" }));
        throw new Error(errorData.detail || "Failed to validate file");
    }
    
    return res.json();
}
