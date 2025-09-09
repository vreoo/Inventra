"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";

export default function ConfigPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const fileId = searchParams.get("fileId") || "demo-file";

    const [showAdvanced, setShowAdvanced] = useState(false);
    const [seasonality, setSeasonality] = useState("auto");
    const [changepointRange, setChangepointRange] = useState("0.8");

    const handleSubmit = async () => {
        // Simulate API call
        const jobId = `job-${Date.now()}`;
        router.push(`/results?jobId=${jobId}`);
    };

    return (
        <main className="p-8 max-w-2xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">
                Configure Forecast Settings
            </h1>

            <Card>
                <CardContent className="space-y-6 p-6">
                    <div className="flex justify-between items-center">
                        <Label htmlFor="advanced">Show Advanced Settings</Label>
                        <Switch
                            id="advanced"
                            checked={showAdvanced}
                            onCheckedChange={setShowAdvanced}
                        />
                    </div>

                    {showAdvanced && (
                        <div className="space-y-4">
                            <div>
                                <Label htmlFor="seasonality">Seasonality</Label>
                                <Input
                                    id="seasonality"
                                    value={seasonality}
                                    onChange={(e) =>
                                        setSeasonality(e.target.value)
                                    }
                                />
                            </div>
                            <div>
                                <Label htmlFor="changepoint">
                                    Changepoint Range
                                </Label>
                                <Input
                                    id="changepoint"
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    max="1"
                                    value={changepointRange}
                                    onChange={(e) =>
                                        setChangepointRange(e.target.value)
                                    }
                                />
                            </div>
                        </div>
                    )}

                    <Button onClick={handleSubmit} className="w-full">
                        Start Forecast
                    </Button>
                </CardContent>
            </Card>
        </main>
    );
}
