type EnvWindow = Window & {
  ENV?: {
    NEXT_PUBLIC_API_BASE_URL?: string;
  };
};

const DEFAULT_API_BASE_URL = "http://localhost:8000/api";

const API_BASE_URL =
  typeof window !== "undefined"
    ? (window as EnvWindow).ENV?.NEXT_PUBLIC_API_BASE_URL ??
      DEFAULT_API_BASE_URL
    : DEFAULT_API_BASE_URL;

export type ForecastMode = "inventory" | "demand";

export interface ColumnMapping {
  date?: string | null;
  sku?: string | null;
  demand?: string | null;
  inventory?: string | null;
  lead_time?: string | null;
  name?: string | null;
  promo_flag?: string | null;
  holiday_flag?: string | null;
}

export interface ValidationAnomaly {
  unique_id: string;
  date: string;
  value: number;
  z_score: number;
}

export interface ValidationSummary {
  rows: number;
  columns: string[];
  detected_frequency?: string | null;
  date_coverage_pct?: number | null;
  missing_by_field?: Record<string, number>;
  anomalies?: ValidationAnomaly[];
}

export interface UploadValidationInfo {
  rows: number;
  columns: string[];
  date_columns: string[];
  numeric_columns: string[];
  text_columns: string[];
  detected_frequency?: string;
  date_coverage_pct?: number;
  missing_by_field?: Record<string, number>;
  anomalies?: ValidationAnomaly[];
}

export interface UploadValidation {
  valid: boolean;
  errors: string[];
  warnings: string[];
  info: UploadValidationInfo;
}

export interface UploadResponse {
  fileId: string;
  filename: string;
  mode?: ForecastMode;
  schema_version?: string;
  validation: UploadValidation;
  mapping?: ColumnMapping;
  summary?: ValidationSummary;
  uploaded_at?: string;
}

interface UploadResponseLike {
  validation?: UploadValidation;
  valid?: unknown;
  errors?: unknown;
  warnings?: unknown;
  info?: Partial<UploadValidationInfo>;
  rows?: unknown;
  columns?: unknown;
  date_columns?: unknown;
  numeric_columns?: unknown;
  text_columns?: unknown;
  summary?: ValidationSummary;
  validation_summary?: ValidationSummary;
  mapping?: ColumnMapping;
  fileId?: unknown;
  filename?: unknown;
  mode?: ForecastMode;
  schema_version?: string;
  uploaded_at?: unknown;
  [key: string]: unknown;
}

export interface ForecastConfig {
  model?:
    | "AutoARIMA"
    | "AutoETS"
    | "SeasonalNaive"
    | "Naive"
    | "RandomWalkWithDrift"
    | "SklearnModel"
    | "CrostonClassic"
    | "CrostonOptimized"
    | "CrostonSBA"
    | "TBATS";
  horizon?: number;
  frequency?: string;
  confidence_level?: number;
  seasonal_length?: number | null;
  service_level?: number;
  lead_time_days_default?: number;
  safety_stock_policy?: string;
  reorder_policy?: string;
  enable_tbats?: boolean;
  include_external_factors?: boolean;
  enable_ai_analysis?: boolean;
  location?: string;
  country_code?: string;
}

// External factors data structures (retained for future use)
export interface WeatherData {
  date: string;
  temperature: number;
  humidity: number;
  precipitation: number;
  wind_speed: number;
  weather_condition: string;
}

export interface HolidayData {
  date: string;
  name: string;
  type: "national" | "regional" | "religious" | "cultural";
  impact_level: "low" | "medium" | "high";
}

export interface FactorAttribution {
  factor_type: "weather" | "holiday" | "seasonal" | "trend";
  factor_name: string;
  impact_score: number;
  confidence: number;
  description: string;
}

export interface AIAnalysis {
  trend_explanation: string;
  factor_summary: string;
  recommendations: string[];
  risk_assessment: string;
  confidence_score: number;
}

export interface ForecastSeries {
  product_id: string;
  product_name?: string;
  model_used: string;
  mode?: ForecastMode;
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
    MAE?: number | null;
    MSE?: number | null;
    RMSE?: number | null;
    MAPE?: number | null;
  };
  safety_stock?: number | null;
  recommended_order_qty?: number | null;
  service_level?: number | null;
  lead_time_days?: number | null;
  starting_inventory?: number | null;
  demand_frequency?: string | null;
  schema_version?: string | null;
  external_factors_used?: string[];
  factor_attributions?: FactorAttribution[];
  weather_impact_summary?: string | null;
  holiday_impact_summary?: string | null;
  ai_trend_explanation?: string | null;
  ai_factor_summary?: string | null;
  ai_recommendations?: string[];
  ai_risk_assessment?: string | null;
  baseline_accuracy?: number | null;
  enhanced_accuracy?: number | null;
  accuracy_improvement?: number | null;
  external_factor_confidence?: number | null;
  external_factors?: {
    weather_data?: WeatherData[];
    holiday_data?: HolidayData[];
    factor_attributions?: FactorAttribution[];
  };
  ai_analysis?: AIAnalysis;
  data_quality_score?: number;
}

export interface ForecastResult {
  jobId: string;
  fileId: string;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  created_at: string;
  completed_at?: string;
  error_message?: string;
  mode?: ForecastMode;
  schema_version?: string;
  mapping?: ColumnMapping;
  validation?: ValidationSummary;
  results?: ForecastSeries[];
  config?: ForecastConfig;
}

export interface ForecastJobResponse {
  jobId: string;
}

export interface ForecastJobOptions {
  mode?: ForecastMode;
  schemaVersion?: string;
  mappingOverrides?: Partial<ColumnMapping> | null;
}

export interface LatestConfig {
  version: string;
  updated_at: string | null;
  global: Record<string, unknown>;
  per_sku: Record<string, Record<string, unknown>>;
}

export interface ConfigRecord {
  timestamp: string;
  version: string;
  scope: "global" | "sku";
  target?: string | null;
  settings: Record<string, unknown>;
  author?: string | null;
}

export interface ConfigUpdatePayload {
  scope?: "global" | "sku";
  target?: string | null;
  settings: Record<string, unknown>;
  author?: string | null;
}

const DEFAULT_UPLOAD_SCHEMA = "1.0.0";

function normalizeUploadResponse(data: unknown): UploadResponse {
  if (typeof data !== "object" || data === null) {
    throw new Error("Unexpected upload response payload");
  }

  const payload = data as UploadResponseLike;

  const normalizeStringArray = (value: unknown): string[] =>
    Array.isArray(value)
      ? value.filter((item): item is string => typeof item === "string")
      : [];

  const info: UploadValidationInfo = {
    rows:
      typeof payload.info?.rows === "number"
        ? payload.info.rows
        : typeof payload.rows === "number"
        ? payload.rows
        : 0,
    columns: normalizeStringArray(payload.info?.columns ?? payload.columns),
    date_columns: normalizeStringArray(
      payload.info?.date_columns ?? payload.date_columns
    ),
    numeric_columns: normalizeStringArray(
      payload.info?.numeric_columns ?? payload.numeric_columns
    ),
    text_columns: normalizeStringArray(
      payload.info?.text_columns ?? payload.text_columns
    ),
    detected_frequency: payload.info?.detected_frequency,
    date_coverage_pct: payload.info?.date_coverage_pct,
    missing_by_field: payload.info?.missing_by_field,
    anomalies: payload.info?.anomalies as ValidationAnomaly[] | undefined,
  };

  const validation: UploadValidation = payload.validation
    ? payload.validation
    : {
        valid: typeof payload.valid === "boolean" ? payload.valid : true,
        errors: normalizeStringArray(payload.errors),
        warnings: normalizeStringArray(payload.warnings),
        info,
      };

  const summary: ValidationSummary | undefined =
    payload.summary ||
    payload.validation_summary ||
    (
      validation.info as UploadValidationInfo & {
        summary?: ValidationSummary;
      }
    )?.summary;

  const mapping: ColumnMapping | undefined =
    payload.mapping ||
    (
      validation as UploadValidation & {
        mapping?: ColumnMapping;
        info?: UploadValidationInfo & { mapping?: ColumnMapping };
      }
    ).mapping ||
    (
      validation.info as UploadValidationInfo & {
        mapping?: ColumnMapping;
      }
    )?.mapping;

  if (
    typeof payload.fileId !== "string" ||
    typeof payload.filename !== "string"
  ) {
    throw new Error("Upload response missing file metadata");
  }

  return {
    fileId: payload.fileId,
    filename: payload.filename,
    mode: payload.mode,
    schema_version: payload.schema_version,
    validation,
    mapping,
    summary,
    uploaded_at:
      typeof payload.uploaded_at === "string" ? payload.uploaded_at : undefined,
  };
}

export async function uploadFile(
  formData: FormData,
  options?: { mode?: ForecastMode; schemaVersion?: string }
): Promise<UploadResponse> {
  const mode = options?.mode ?? "inventory";
  const schemaVersion = options?.schemaVersion ?? DEFAULT_UPLOAD_SCHEMA;

  if (!formData.has("mode")) {
    formData.append("mode", mode);
  }
  if (!formData.has("schema_version")) {
    formData.append("schema_version", schemaVersion);
  }

  const res = await fetch(`${API_BASE_URL}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res
      .json()
      .catch(() => ({ detail: "Failed to upload file" }));
    throw new Error(errorData.detail || "Failed to upload file");
  }

  const data = await res.json();
  return normalizeUploadResponse(data);
}

export async function createForecastJob(
  fileId: string,
  config: ForecastConfig = {},
  options: ForecastJobOptions = {}
): Promise<ForecastJobResponse> {
  const defaultConfig: ForecastConfig = {
    model: "AutoARIMA",
    horizon: 30,
    frequency: "D",
    confidence_level: 0.95,
    service_level: 0.95,
    lead_time_days_default: 7,
    safety_stock_policy: "ss_z_score",
    reorder_policy: "continuous_review",
    ...config,
  };

  const bodyPayload = {
    fileId,
    config: defaultConfig,
    mode: options.mode ?? "inventory",
    schema_version: options.schemaVersion,
    mapping_overrides: options.mappingOverrides ?? undefined,
  };

  const res = await fetch(`${API_BASE_URL}/forecast`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(bodyPayload),
  });

  if (!res.ok) {
    const errorData = await res
      .json()
      .catch(() => ({ detail: "Failed to create forecast job" }));
    throw new Error(errorData.detail || "Failed to create forecast job");
  }

  return res.json();
}

export async function getForecastResult(
  jobId: string
): Promise<ForecastResult> {
  const res = await fetch(`${API_BASE_URL}/forecast/${jobId}`);

  if (!res.ok) {
    const errorData = await res
      .json()
      .catch(() => ({ detail: "Failed to fetch forecast result" }));
    throw new Error(errorData.detail || "Failed to fetch forecast result");
  }

  return res.json();
}

export async function validateFile(fileId: string): Promise<UploadResponse> {
  const res = await fetch(`${API_BASE_URL}/upload/${fileId}/validate`);

  if (!res.ok) {
    const errorData = await res
      .json()
      .catch(() => ({ detail: "Failed to validate file" }));
    throw new Error(errorData.detail || "Failed to validate file");
  }

  const data = await res.json();
  return normalizeUploadResponse(data);
}

export async function getLatestConfig(): Promise<LatestConfig> {
  const res = await fetch(`${API_BASE_URL}/configs`);
  if (!res.ok) {
    throw new Error("Failed to load configuration");
  }
  return res.json();
}

export async function updateConfig(
  payload: ConfigUpdatePayload
): Promise<ConfigRecord> {
  const res = await fetch(`${API_BASE_URL}/configs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res
      .json()
      .catch(() => ({ detail: "Failed to update configuration" }));
    throw new Error(errorData.detail || "Failed to update configuration");
  }
  return res.json();
}

export async function getConfigHistory(
  limit?: number
): Promise<ConfigRecord[]> {
  const query = typeof limit === "number" ? `?limit=${limit}` : "";
  const res = await fetch(`${API_BASE_URL}/configs/history${query}`);
  if (!res.ok) {
    throw new Error("Failed to load configuration history");
  }
  return res.json();
}
