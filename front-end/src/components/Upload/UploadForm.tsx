"use client";

import { useState } from "react";
import * as Papa from "papaparse";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export function UploadForm() {
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<any[][]>([]);
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        if (f) {
            setFile(f);
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

        // Placeholder for API call to upload
        await new Promise((resolve) => setTimeout(resolve, 1500));

        // Navigate to results page with dummy job ID
        router.push("/results?jobId=dummy-1234");
    };

    return (
        <div className="w-full max-w-xl space-y-6">
            <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />

            {preview.length > 0 && (
                <div className="border rounded p-4 bg-white shadow-sm">
                    <h2 className="text-lg font-medium mb-2">Preview:</h2>
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
                                        <td
                                            key={j}
                                            className="px-2 py-1 border-b"
                                        >
                                            {val as string}
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            <Button
                onClick={handleUpload}
                disabled={!file || loading}
                className="w-full"
            >
                {loading ? "Uploading..." : "Upload & Forecast"}
            </Button>
        </div>
    );
}
