"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Label } from "@/components/ui/label";
import {
  createForecastJob,
  uploadFile,
  UploadResponse,
  ForecastConfig,
  ForecastMode,
  ColumnMapping,
  ValidationSummary,
} from "@/services/api";
import {
  CheckCircle,
  AlertTriangle,
  XCircle,
  Calendar,
  Hash,
  Type,
  Eye,
  EyeOff,
  Info,
  HelpCircle,
  Target,
} from "lucide-react";
import ForecastSettings from "@/components/Settings/ForecastSettings";

const DEFAULT_SERVICE_LEVEL = 0.95;
const DEFAULT_LEAD_TIME = 7;

const MAPPING_FIELDS: Array<{
  key: keyof ColumnMapping;
  label: string;
  helper?: string;
  required?: boolean;
}> = [
  {
    key: "date",
    label: "Demand date",
    helper: "Timestamps for historical demand observations",
    required: true,
  },
  {
    key: "sku",
    label: "SKU / Product ID",
    helper: "Unique identifier for each product",
  },
  {
    key: "demand",
    label: "Demand quantity",
    helper: "Number of units sold or consumed per period",
    required: true,
  },
  {
    key: "inventory",
    label: "Current inventory",
    helper: "On-hand stock snapshot at upload time",
  },
  {
    key: "lead_time",
    label: "Lead time (days)",
    helper: "Supplier lead time for replenishment",
  },
  {
    key: "name",
    label: "Product name",
    helper: "Readable description for results",
  },
];

export default function UploadPage() {
  const demandPlanningEnabled =
    process.env.NEXT_PUBLIC_DEMAND_PLANNING_ENABLED === "true";
  const defaultMode: ForecastMode = demandPlanningEnabled
    ? "demand"
    : "inventory";

  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [csvPreview, setCsvPreview] = useState<string[][]>([]);
  const [error, setError] = useState<string | null>(null);
  const [uploadResponse, setUploadResponse] = useState<UploadResponse | null>(
    null
  );
  const [fileId, setFileId] = useState<string | null>(null);
  const [schemaVersion, setSchemaVersion] = useState<string | undefined>();
  const [mode, setMode] = useState<ForecastMode>(defaultMode);
  const [isUploading, setIsUploading] = useState(false);
  const [showDetailedPreview, setShowDetailedPreview] = useState(false);
  const [forecastConfig, setForecastConfig] = useState<ForecastConfig>({});
  const [serviceLevel, setServiceLevel] = useState(DEFAULT_SERVICE_LEVEL);
  const [leadTimeDefault, setLeadTimeDefault] = useState(DEFAULT_LEAD_TIME);
  const [safetyStockPolicy, setSafetyStockPolicy] = useState("ss_z_score");
  const [reorderPolicy, setReorderPolicy] = useState("continuous_review");
  const [mappingOverrides, setMappingOverrides] = useState<
    Partial<ColumnMapping>
  >({});
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validationResult = uploadResponse?.validation ?? null;
  const validationSummary: ValidationSummary | null =
    uploadResponse?.summary ?? null;
  const mapping = uploadResponse?.mapping ?? null;

  useEffect(() => {
    if (!uploadResponse) return;
    setSchemaVersion(uploadResponse.schema_version);
    setMappingOverrides({});
  }, [uploadResponse]);

  const columns = useMemo(
    () => validationResult?.info.columns ?? [],
    [validationResult?.info.columns]
  );

  const selectedMappingValue = (key: keyof ColumnMapping) => {
    if (mappingOverrides[key] !== undefined) {
      return mappingOverrides[key] ?? "";
    }
    return (mapping?.[key] as string | null | undefined) ?? "";
  };

  const handleMappingChange = (key: keyof ColumnMapping, value: string) => {
    setMappingOverrides((prev) => ({
      ...prev,
      [key]: value ? value : null,
    }));
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    setError(null);
    setUploadResponse(null);
    setFileId(null);

    if (!selected) return;

    if (
      selected.type !== "application/vnd.ms-excel" &&
      selected.type !== "text/csv"
    ) {
      setError("Only CSV files are allowed.");
      return;
    }

    const maxSize = 5 * 1024 * 1024;
    if (selected.size > maxSize) {
      setError("File is too large. Max size is 5MB.");
      return;
    }

    setFile(selected);
    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append("file", selected);

      const response = await uploadFile(formData, { mode });
      setUploadResponse(response);
      setFileId(response.fileId);

      const text = await selected.text();
      const rows = text
        .split("\n")
        .slice(0, 6)
        .map((line) => line.split(","));
      setCsvPreview(rows);
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Failed to process file."
      );
      console.error(error);
    } finally {
      setIsUploading(false);
    }
  };

  const handleSubmit = async () => {
    if (!fileId || !validationResult?.valid) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const { jobId } = await createForecastJob(
        fileId,
        {
          ...forecastConfig,
          service_level: serviceLevel,
          lead_time_days_default: leadTimeDefault,
          safety_stock_policy: safetyStockPolicy,
          reorder_policy: reorderPolicy,
        },
        {
          mode,
          schemaVersion,
          mappingOverrides:
            Object.keys(mappingOverrides).length > 0
              ? mappingOverrides
              : undefined,
        }
      );

      router.push(`/results?jobId=${jobId}`);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create forecast job."
      );
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setCsvPreview([]);
    setError(null);
    setUploadResponse(null);
    setFileId(null);
    setSchemaVersion(undefined);
    setShowDetailedPreview(false);
    setForecastConfig({});
    setServiceLevel(DEFAULT_SERVICE_LEVEL);
    setLeadTimeDefault(DEFAULT_LEAD_TIME);
    setSafetyStockPolicy("ss_z_score");
    setReorderPolicy("continuous_review");
    setMappingOverrides({});
  };

  const getColumnTypeIcon = (columnName: string) => {
    if (!validationResult) return null;

    if (validationResult.info.date_columns.includes(columnName)) {
      return <Calendar className="w-4 h-4 text-blue-500" />;
    }
    if (validationResult.info.numeric_columns.includes(columnName)) {
      return <Hash className="w-4 h-4 text-green-500" />;
    }
    return <Type className="w-4 h-4 text-gray-500" />;
  };

  const renderValidationStatus = () => {
    if (!validationResult) return null;

    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            {validationResult.valid ? (
              <CheckCircle className="w-5 h-5 text-green-500" />
            ) : (
              <XCircle className="w-5 h-5 text-red-500" />
            )}
            File Validation
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {validationResult.errors.length > 0 && (
            <div className="rounded-md border border-red-200 bg-red-50 p-3">
              <div className="mb-2 flex items-center gap-2">
                <XCircle className="h-4 w-4 text-red-500" />
                <span className="font-medium text-red-800">Errors</span>
              </div>
              <ul className="space-y-1 text-sm text-red-700">
                {validationResult.errors.map((item, idx) => (
                  <li key={idx}>• {item}</li>
                ))}
              </ul>
            </div>
          )}

          {validationResult.warnings.length > 0 && (
            <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3">
              <div className="mb-2 flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                <span className="font-medium text-yellow-800">Warnings</span>
              </div>
              <ul className="space-y-1 text-sm text-yellow-700">
                {validationResult.warnings.map((item, idx) => (
                  <li key={idx}>• {item}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid gap-4 text-sm md:grid-cols-3">
            <div>
              <span className="font-medium">Rows:</span>{" "}
              {validationResult.info.rows}
            </div>
            <div>
              <span className="font-medium">Columns:</span>{" "}
              {validationResult.info.columns.length}
            </div>
            {validationSummary?.detected_frequency && (
              <div>
                <span className="font-medium">Detected frequency:</span>{" "}
                {validationSummary.detected_frequency}
              </div>
            )}
            {typeof validationSummary?.date_coverage_pct === "number" && (
              <div>
                <span className="font-medium">Date coverage:</span>{" "}
                {(validationSummary.date_coverage_pct * 100).toFixed(1)}%
              </div>
            )}
          </div>

          {validationSummary?.anomalies &&
            validationSummary.anomalies.length > 0 && (
              <div className="rounded-md border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
                <span className="font-medium">Anomalies detected:</span>{" "}
                {validationSummary.anomalies.length} points exceed |z| ≥ 3.0.
              </div>
            )}
        </CardContent>
      </Card>
    );
  };

  const renderMappingWizard = () => {
    if (mode !== "demand" || !uploadResponse) return null;

    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Info className="h-5 w-5 text-blue-500" />
            Column Mapping
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Confirm how each column should be interpreted. Auto-detected
            selections can be overridden at any time before generating the
            forecast.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            {MAPPING_FIELDS.map((field) => {
              const value = selectedMappingValue(field.key) ?? "";
              const missing = field.required && !value;
              return (
                <div key={field.key} className="space-y-2">
                  <Label className="flex items-center gap-2 text-sm font-medium">
                    {field.label}
                    {field.required && (
                      <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs text-red-700">
                        Required
                      </span>
                    )}
                  </Label>
                  <select
                    value={value}
                    onChange={(event) =>
                      handleMappingChange(field.key, event.target.value)
                    }
                    className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                      missing ? "border-red-300" : "border-gray-200"
                    }`}
                  >
                    <option value="">
                      {mapping?.[field.key]
                        ? `Auto: ${mapping[field.key]}`
                        : "Select a column"}
                    </option>
                    {columns.map((column) => (
                      <option key={column} value={column}>
                        {column}
                      </option>
                    ))}
                  </select>
                  {field.helper && (
                    <p className="text-xs text-muted-foreground">
                      {field.helper}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderPolicyConfig = () => (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-lg">
          <Target className="h-5 w-5 text-purple-500" />
          Service Level & Policies
        </CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <div className="space-y-1">
          <Label htmlFor="service-level">Target service level</Label>
          <Input
            id="service-level"
            type="number"
            min={0.5}
            max={0.999}
            step={0.01}
            value={serviceLevel}
            onChange={(event) =>
              setServiceLevel(parseFloat(event.target.value) || 0.95)
            }
          />
          <p className="text-xs text-muted-foreground">
            Probability of meeting demand without a stockout during lead time.
          </p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="lead-time-default">Default lead time (days)</Label>
          <Input
            id="lead-time-default"
            type="number"
            min={0}
            max={365}
            value={leadTimeDefault}
            onChange={(event) =>
              setLeadTimeDefault(parseInt(event.target.value || "0", 10))
            }
          />
          <p className="text-xs text-muted-foreground">
            Used when a SKU-specific lead time is not supplied in the file.
          </p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="safety-stock-policy">Safety stock policy</Label>
          <select
            id="safety-stock-policy"
            className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={safetyStockPolicy}
            onChange={(event) => setSafetyStockPolicy(event.target.value)}
          >
            <option value="ss_z_score">Z-score (normal demand)</option>
            <option value="ss_minmax">Min/max buffer</option>
          </select>
          <p className="text-xs text-muted-foreground">
            Determines how safety stock is computed from demand variability.
          </p>
        </div>
        <div className="space-y-1">
          <Label htmlFor="reorder-policy">Reorder policy</Label>
          <select
            id="reorder-policy"
            className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={reorderPolicy}
            onChange={(event) => setReorderPolicy(event.target.value)}
          >
            <option value="continuous_review">Continuous review</option>
            <option value="periodic_review">Periodic review</option>
          </select>
          <p className="text-xs text-muted-foreground">
            Choose how reorder points are monitored after forecasting.
          </p>
        </div>
      </CardContent>
    </Card>
  );

  const renderPreviewTable = () => {
    if (csvPreview.length === 0) return null;
    return (
      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>Preview</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetailedPreview(!showDetailedPreview)}
          >
            {showDetailedPreview ? (
              <span className="flex items-center gap-2">
                <EyeOff className="h-4 w-4" /> Hide preview
              </span>
            ) : (
              <span className="flex items-center gap-2">
                <Eye className="h-4 w-4" /> Show preview
              </span>
            )}
          </Button>
        </CardHeader>
        {showDetailedPreview && (
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  {csvPreview[0]?.map((header, idx) => (
                    <TableHead key={idx}>
                      <div className="flex items-center gap-2">
                        {getColumnTypeIcon(header)}
                        <span>{header}</span>
                      </div>
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {csvPreview.slice(1).map((row, rowIndex) => (
                  <TableRow key={rowIndex}>
                    {row.map((cell, cellIndex) => (
                      <TableCell key={cellIndex}>{cell}</TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        )}
      </Card>
    );
  };

  const canSubmit = Boolean(fileId && validationResult?.valid && !isSubmitting);

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Demand Planning Upload</h1>
          <p className="text-sm text-muted-foreground">
            Provide demand history, on-hand inventory, and lead times to
            forecast reorder needs. Legacy inventory forecasts remain available
            via the inventory mode.
          </p>
        </div>
        {demandPlanningEnabled ? (
          <div className="flex gap-2">
            <Button
              variant={mode === "demand" ? "default" : "outline"}
              size="sm"
              disabled={Boolean(fileId)}
              onClick={() => setMode("demand")}
            >
              Demand planning
            </Button>
            <Button
              variant={mode === "inventory" ? "default" : "outline"}
              size="sm"
              disabled={Boolean(fileId)}
              onClick={() => setMode("inventory")}
            >
              Inventory (legacy)
            </Button>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <HelpCircle className="h-4 w-4" />
            Demand planning beta is disabled; running inventory forecasts.
          </div>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload CSV</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-3 md:flex-row md:items-center">
            <Input
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              disabled={isUploading}
            />
            {file && (
              <span className="text-sm text-muted-foreground">
                Selected: {file.name}
              </span>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            Expect columns for demand quantities, SKU identifiers, optional
            on-hand inventory, and lead times. Daily and weekly data are
            supported.
          </p>
        </CardContent>
      </Card>

      {uploadResponse && (
        <div className="space-y-6">
          {renderValidationStatus()}
          {renderMappingWizard()}
          <ForecastSettings
            validationResult={uploadResponse.validation}
            onConfigChange={setForecastConfig}
            initialConfig={forecastConfig}
          />
          {renderPolicyConfig()}
          {renderPreviewTable()}
        </div>
      )}

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="flex items-center justify-between border-t border-dashed border-gray-200 pt-4">
        <div className="text-xs text-muted-foreground">
          Mode: <span className="font-medium text-foreground">{mode}</span>
          {schemaVersion && (
            <span className="ml-2">Schema {schemaVersion}</span>
          )}
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            onClick={handleReset}
            disabled={isUploading}
          >
            Reset
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {isSubmitting ? "Submitting…" : "Run forecast"}
          </Button>
        </div>
      </div>
    </div>
  );
}
