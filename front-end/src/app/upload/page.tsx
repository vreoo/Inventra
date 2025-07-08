// src/app/upload/page.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

export default function UploadPage() {
    const [file, setFile] = useState<File | null>(null);
    const [csvPreview, setCsvPreview] = useState<string[][]>([]);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const f = e.target.files?.[0];
        setError(null);
        if (!f) return;

        // Validate file type
        if (f.type !== "text/csv") {
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

        // Parse and preview CSV
        const text = await f.text();
        const rows = text
            .split("\n")
            .slice(0, 6)
            .map((line) => line.split(","));
        setCsvPreview(rows);
    };

    const handleSubmit = () => {
        // Placeholder for actual upload logic
        if (!file) return;
        console.log("Uploading file:", file.name);
        // Redirect to results page with dummy job ID
        router.push("/results?jobId=dummy-1234");
    };

    const handleReset = () => {
        setFile(null);
        setCsvPreview([]);
        setError(null);
    };

    return (
        <main className="p-8 min-h-screen bg-white">
            <h1 className="text-2xl font-bold mb-6">Upload Inventory CSV</h1>

            <Card className="max-w-xl">
                <CardContent className="space-y-4 p-4">
                    <Input
                        type="file"
                        accept=".csv"
                        onChange={handleFileChange}
                    />

                    {error && <p className="text-red-500 text-sm">{error}</p>}

                    {csvPreview.length > 0 && (
                        <div className="overflow-x-auto">
                            <Table>
                                <TableHeader>
                                    <TableRow>
                                        {csvPreview[0].map((col, idx) => (
                                            <TableHead key={idx}>
                                                {col}
                                            </TableHead>
                                        ))}
                                    </TableRow>
                                </TableHeader>
                                <TableBody>
                                    {csvPreview.slice(1).map((row, i) => (
                                        <TableRow key={i}>
                                            {row.map((cell, j) => (
                                                <TableCell key={j}>
                                                    {cell}
                                                </TableCell>
                                            ))}
                                        </TableRow>
                                    ))}
                                </TableBody>
                            </Table>
                        </div>
                    )}

                    <div className="flex space-x-2">
                        <Button onClick={handleSubmit} disabled={!file}>
                            Submit
                        </Button>
                        <Button variant="secondary" onClick={handleReset}>
                            Reset
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </main>
    );
}
