"use client";

import { useState } from "react";
import * as Papa from "papaparse";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { uploadFile, createForecastJob, ForecastConfig } from "@/services/api";

export function UploadForm() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<any[][]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationInfo, setValidationInfo] = useState<any>(null);
  const router = useRouter();

  const handleFileChange = (e: any) => {
    const f = e.target.files?.[0];
    if (f) {
      setFile(f);
      setError(null);
      setValidationInfo(null);

      Papa.parse(f, {
        header: true,
        preview: 5,
        complete: (results: Papa.ParseResult<any>) => {
          setPreview(results.data as any[][]);
        },
      });
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      // Upload file
      const formData = new FormData();
      formData.append("file", file);

      const uploadResponse = await uploadFile(formData);
      setValidationInfo(uploadResponse.validation);

      // Create forecast job with default config
      const forecastConfig: ForecastConfig = {
        model: "AutoARIMA",
        horizon: 30,
        frequency: "D",
        confidence_level: 0.95,
      };

      const jobResponse = await createForecastJob(
        uploadResponse.fileId,
        forecastConfig
      );

      // Navigate to results page
      router.push(`/results?jobId=${jobResponse.jobId}`);
    } catch (err: any) {
      console.error("Upload error:", err);
      setError(err.message || "Failed to upload file and create forecast");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full max-w-xl space-y-6">
      <input
        type="file"
        accept=".csv"
        onChange={handleFileChange}
        className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
      />

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <p className="text-red-800 text-sm">{error}</p>
        </div>
      )}

      {validationInfo && (
        <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
          <h3 className="font-medium text-blue-900 mb-2">File Validation</h3>
          <div className="text-sm text-blue-800">
            <p>Rows: {validationInfo.info.rows}</p>
            <p>Columns: {validationInfo.info.columns.join(", ")}</p>
            {validationInfo.info.date_columns.length > 0 && (
              <p>Date columns: {validationInfo.info.date_columns.join(", ")}</p>
            )}
            {validationInfo.info.numeric_columns.length > 0 && (
              <p>
                Numeric columns:{" "}
                {validationInfo.info.numeric_columns.join(", ")}
              </p>
            )}
          </div>
          {validationInfo.warnings.length > 0 && (
            <div className="mt-2">
              <p className="font-medium text-yellow-800">Warnings:</p>
              <ul className="list-disc list-inside text-sm text-yellow-700">
                {validationInfo.warnings.map((warning: string, i: number) => (
                  <li key={i}>{warning}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {preview.length > 0 && (
        <div className="border rounded p-4 bg-white shadow-sm">
          <h2 className="text-lg font-medium mb-2">Preview:</h2>
          <div className="overflow-x-auto">
            <table className="table-auto text-sm w-full">
              <thead>
                <tr>
                  {Object.keys(preview[0] || {}).map((key, i) => (
                    <th
                      key={i}
                      className="px-2 py-1 text-left font-semibold border-b"
                    >
                      {key}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.slice(0, 5).map((row, i) => (
                  <tr key={i}>
                    {Object.values(row).map((val, j) => (
                      <td key={j} className="px-2 py-1 border-b">
                        {val as string}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Button
        onClick={handleUpload}
        disabled={!file || loading}
        className="w-full"
      >
        {loading ? "Uploading & Creating Forecast..." : "Upload & Forecast"}
      </Button>
    </div>
  );
}
