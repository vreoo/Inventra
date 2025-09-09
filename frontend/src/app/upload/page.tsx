// src/app/upload/page.tsx
"use client";

import { useState } from "react";
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
import { createForecastJob, uploadFile, UploadResponse, ForecastConfig } from "@/services/api";
import { CheckCircle, AlertTriangle, XCircle, Calendar, Hash, Type, Eye, EyeOff, Info, HelpCircle } from "lucide-react";
import ForecastSettings from "@/components/Settings/ForecastSettings";

export default function UploadPage() {
    const [file, setFile] = useState<File | null>(null);
    const [csvPreview, setCsvPreview] = useState<string[][]>([]);
    const [error, setError] = useState<string | null>(null);
    const [validationResult, setValidationResult] = useState<UploadResponse["validation"] | null>(null);
    const [fileId, setFileId] = useState<string | null>(null);
    const [isUploading, setIsUploading] = useState(false);
    const [showDetailedPreview, setShowDetailedPreview] = useState(false);
    const [forecastConfig, setForecastConfig] = useState<ForecastConfig>({});
    const [isSubmitting, setIsSubmitting] = useState(false);
    const router = useRouter();

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        setError(null);
        setValidationResult(null);
        setFileId(null);
        if (!f) return;

        console.log("Selected file:", f);

        // Validate file type
        if (f.type !== "application/vnd.ms-excel" && f.type !== "text/csv") {
            setError("Only CSV files are allowed.");
            return;
        }

        // Validate file size (e.g., max 5MB)
        const maxSize = 5 * 1024 * 1024;
        if (f.size > maxSize) {
            setError("File is too large. Max size is 5MB.");
            return;
        }

        setFile(f);
        setIsUploading(true);

        try {
            // Upload file and get validation results
            const formData = new FormData();
            formData.append("file", f);
            
            const uploadResponse = await uploadFile(formData);
            setValidationResult(uploadResponse.validation);
            setFileId(uploadResponse.fileId);

            // Parse and preview CSV for display
            const text = await f.text();
            const rows = text
                .split("\n")
                .slice(0, 6)
                .map((line) => line.split(","));
            setCsvPreview(rows);
        } catch (err: any) {
            setError(err.message || "Failed to process file.");
            console.error(err);
        } finally {
            setIsUploading(false);
        }
    };

    const handleSubmit = async () => {
        if (!fileId || !validationResult?.valid) return;

        setIsSubmitting(true);
        setError(null);

        try {
            const { jobId } = await createForecastJob(fileId, forecastConfig);
            router.push(`/results?jobId=${jobId}`);
        } catch (err: any) {
            setError("Failed to create forecast job. Please try again.");
            console.error(err);
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleReset = () => {
        setFile(null);
        setCsvPreview([]);
        setError(null);
        setValidationResult(null);
        setFileId(null);
        setShowDetailedPreview(false);
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
            <Card className="mt-4">
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
                    {/* Errors */}
                    {validationResult.errors.length > 0 && (
                        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
                            <div className="flex items-center gap-2 mb-2">
                                <XCircle className="w-4 h-4 text-red-500" />
                                <span className="font-medium text-red-800">Errors</span>
                            </div>
                            <ul className="text-sm text-red-700 space-y-1">
                                {validationResult.errors.map((error, idx) => (
                                    <li key={idx}>• {error}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Warnings */}
                    {validationResult.warnings.length > 0 && (
                        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                            <div className="flex items-center gap-2 mb-2">
                                <AlertTriangle className="w-4 h-4 text-yellow-500" />
                                <span className="font-medium text-yellow-800">Warnings</span>
                            </div>
                            <ul className="text-sm text-yellow-700 space-y-1">
                                {validationResult.warnings.map((warning, idx) => (
                                    <li key={idx}>• {warning}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* File Info */}
                    <div className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                            <span className="font-medium">Rows:</span> {validationResult.info.rows}
                        </div>
                        <div>
                            <span className="font-medium">Columns:</span> {validationResult.info.columns.length}
                        </div>
                    </div>

                    {/* Column Types */}
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="font-medium text-sm">Column Analysis</span>
                            <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => setShowDetailedPreview(!showDetailedPreview)}
                                className="h-6 px-2"
                            >
                                {showDetailedPreview ? (
                                    <EyeOff className="w-4 h-4" />
                                ) : (
                                    <Eye className="w-4 h-4" />
                                )}
                            </Button>
                        </div>
                        
                        {showDetailedPreview && (
                            <div className="grid grid-cols-1 gap-2 text-xs">
                                {validationResult.info.date_columns.length > 0 && (
                                    <div className="flex items-center gap-2">
                                        <Calendar className="w-3 h-3 text-blue-500" />
                                        <span>Date columns: {validationResult.info.date_columns.join(", ")}</span>
                                    </div>
                                )}
                                {validationResult.info.numeric_columns.length > 0 && (
                                    <div className="flex items-center gap-2">
                                        <Hash className="w-3 h-3 text-green-500" />
                                        <span>Numeric columns: {validationResult.info.numeric_columns.join(", ")}</span>
                                    </div>
                                )}
                                {validationResult.info.text_columns.length > 0 && (
                                    <div className="flex items-center gap-2">
                                        <Type className="w-3 h-3 text-gray-500" />
                                        <span>Text columns: {validationResult.info.text_columns.join(", ")}</span>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        );
    };

    return (
        <main className="flex flex-col p-8 min-h-screen bg-white items-center justify-center">
            <h1 className="text-2xl font-bold mb-6">Upload Inventory CSV</h1>

            <div className="max-w-4xl space-y-6">
                <Card>
                    <CardContent className="space-y-4 p-4">
                        <Input
                            type="file"
                            accept=".csv"
                            onChange={handleFileChange}
                            disabled={isUploading}
                        />

                        {error && <p className="text-red-500 text-sm">{error}</p>}
                        {isUploading && <p className="text-blue-500 text-sm">Processing file...</p>}

                        <div className="flex space-x-2">
                            <Button variant="secondary" onClick={handleReset}>
                                Reset
                            </Button>
                        </div>
                    </CardContent>
                </Card>

                {/* Validation Status */}
                {renderValidationStatus()}

                {/* Forecast Settings */}
                <ForecastSettings
                    validationResult={validationResult}
                    onConfigChange={setForecastConfig}
                    onSubmit={handleSubmit}
                    isSubmitting={isSubmitting}
                />

                {/* Enhanced CSV Preview */}
                {csvPreview.length > 0 && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                Data Preview
                                <span className="text-sm font-normal text-gray-500">
                                    (First 5 rows)
                                </span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <div className="overflow-x-auto">
                                <Table>
                                    <TableHeader>
                                        <TableRow>
                                            {csvPreview[0].map((col, idx) => (
                                                <TableHead key={idx} className="min-w-[120px]">
                                                    <div className="flex items-center gap-2">
                                                        {getColumnTypeIcon(col)}
                                                        <span>{col}</span>
                                                    </div>
                                                </TableHead>
                                            ))}
                                        </TableRow>
                                    </TableHeader>
                                    <TableBody>
                                        {csvPreview.slice(1).map((row, i) => (
                                            <TableRow key={i}>
                                                {row.map((cell, j) => (
                                                    <TableCell key={j} className="font-mono text-sm">
                                                        {cell || <span className="text-gray-400 italic">empty</span>}
                                                    </TableCell>
                                                ))}
                                            </TableRow>
                                        ))}
                                    </TableBody>
                                </Table>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Helpful Tips */}
                <Card className="border-blue-100 bg-blue-50/30">
                    <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-base text-blue-800">
                            <HelpCircle className="w-5 h-5" />
                            Tips for Better Forecasting
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                            <div className="space-y-2">
                                <div className="flex items-start gap-2">
                                    <Calendar className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <span className="font-medium">Date Format:</span>
                                        <p className="text-gray-600">Use consistent date formats (YYYY-MM-DD, MM/DD/YYYY, etc.)</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-2">
                                    <Hash className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <span className="font-medium">Data Quality:</span>
                                        <p className="text-gray-600">More historical data (6+ months) improves forecast accuracy</p>
                                    </div>
                                </div>
                            </div>
                            <div className="space-y-2">
                                <div className="flex items-start gap-2">
                                    <Info className="w-4 h-4 text-purple-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <span className="font-medium">Expected Columns:</span>
                                        <p className="text-gray-600">date, product_id, quantity, product_name (optional)</p>
                                    </div>
                                </div>
                                <div className="flex items-start gap-2">
                                    <Type className="w-4 h-4 text-gray-500 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <span className="font-medium">Missing Data:</span>
                                        <p className="text-gray-600">Fill gaps in your data for better predictions</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </main>
    );
}
