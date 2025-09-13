"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { 
    Select, 
    SelectContent, 
    SelectItem, 
    SelectTrigger, 
    SelectValue 
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { 
    AlertTriangle, 
    Info, 
    Settings, 
    Zap, 
    TrendingUp, 
    Calendar,
    Package,
    Clock,
    Target,
    HelpCircle
} from "lucide-react";
import { ForecastConfig, UploadResponse } from "@/services/api";

// Use case definitions for warehouse inventory
const USE_CASES = {
    fast_moving: {
        label: "Fast-Moving Items",
        description: "High-turnover products with frequent restocking",
        icon: <Zap className="w-4 h-4" />,
        model: "AutoARIMA" as const,
        horizon: 14,
        confidence_level: 0.90,
        seasonal_length: 7,
        frequency: "D"
    },
    seasonal: {
        label: "Seasonal Products",
        description: "Items with predictable seasonal patterns",
        icon: <Calendar className="w-4 h-4" />,
        model: "AutoETS" as const,
        horizon: 90,
        confidence_level: 0.95,
        seasonal_length: 30,
        frequency: "D"
    },
    stable: {
        label: "Stable Inventory",
        description: "Consistent demand with minimal fluctuation",
        icon: <Package className="w-4 h-4" />,
        model: "SeasonalNaive" as const,
        horizon: 30,
        confidence_level: 0.95,
        seasonal_length: 7,
        frequency: "D"
    },
    trending: {
        label: "Growing/Declining Items",
        description: "Products with clear upward or downward trends",
        icon: <TrendingUp className="w-4 h-4" />,
        model: "AutoARIMA" as const,
        horizon: 60,
        confidence_level: 0.85,
        seasonal_length: null,
        frequency: "D"
    },
    new_product: {
        label: "New Products",
        description: "Recently introduced items with limited history",
        icon: <Target className="w-4 h-4" />,
        model: "RandomWalkWithDrift" as const,
        horizon: 21,
        confidence_level: 0.80,
        seasonal_length: null,
        frequency: "D"
    },
    ml_model: {
        label: "Machine Learning",
        description: "Scikit-learn based model for complex patterns",
        icon: <Zap className="w-4 h-4" />,
        model: "SklearnModel" as const,
        horizon: 30,
        confidence_level: 0.95,
        seasonal_length: 7,
        frequency: "D"
    }
};

interface DataInsights {
    recommendedUseCase: keyof typeof USE_CASES;
    dataQuality: 'excellent' | 'good' | 'fair' | 'poor';
    seasonalityDetected: boolean;
    trendDetected: boolean;
    volatility: 'low' | 'medium' | 'high';
    dataPoints: number;
    timeSpan: number; // days
    warnings: string[];
    recommendations: string[];
}

interface ForecastSettingsProps {
    validationResult: UploadResponse["validation"] | null;
    onConfigChange: (config: ForecastConfig) => void;
    initialConfig?: ForecastConfig;
    onSubmit?: () => void;
    isSubmitting?: boolean;
}

export default function ForecastSettings({ 
    validationResult, 
    onConfigChange, 
    initialConfig,
    onSubmit,
    isSubmitting = false
}: ForecastSettingsProps) {
    const [selectedUseCase, setSelectedUseCase] = useState<keyof typeof USE_CASES>('stable');
    const [isAdvancedMode, setIsAdvancedMode] = useState(false);
    const [config, setConfig] = useState<ForecastConfig>({
        model: "AutoARIMA",
        horizon: 30,
        frequency: "D",
        confidence_level: 0.95,
        seasonal_length: 7,
        ...initialConfig
    });
    const [dataInsights, setDataInsights] = useState<DataInsights | null>(null);

    // Analyze uploaded data and generate insights
    useEffect(() => {
        if (validationResult?.valid && validationResult.info) {
            const insights = analyzeData(validationResult.info);
            setDataInsights(insights);
            
            // Auto-select recommended use case
            setSelectedUseCase(insights.recommendedUseCase);
            
            // Apply recommended configuration
            const recommendedConfig = USE_CASES[insights.recommendedUseCase];
            const newConfig = {
                ...config,
                ...recommendedConfig,
                seasonal_length: insights.seasonalityDetected ? recommendedConfig.seasonal_length : null
            };
            setConfig(newConfig);
            onConfigChange(newConfig);
        }
    }, [validationResult]);

    // Update config when use case changes
    useEffect(() => {
        if (!isAdvancedMode) {
            const useCaseConfig = USE_CASES[selectedUseCase];
            const newConfig: ForecastConfig = {
                model: useCaseConfig.model,
                horizon: useCaseConfig.horizon,
                frequency: useCaseConfig.frequency,
                confidence_level: useCaseConfig.confidence_level,
                seasonal_length: dataInsights?.seasonalityDetected ? useCaseConfig.seasonal_length : null
            };
            setConfig(newConfig);
            onConfigChange(newConfig);
        }
    }, [selectedUseCase, isAdvancedMode]);

    const analyzeData = (info: UploadResponse["validation"]["info"]): DataInsights => {
        const dataPoints = info.rows;
        const hasDateColumn = info.date_columns.length > 0;
        const hasQuantityColumn = info.numeric_columns.length > 0;
        
        // Estimate time span (assuming daily data for now)
        const timeSpan = dataPoints;
        
        // Determine data quality
        let dataQuality: DataInsights['dataQuality'] = 'poor';
        if (dataPoints >= 90 && hasDateColumn && hasQuantityColumn) {
            dataQuality = 'excellent';
        } else if (dataPoints >= 30 && hasDateColumn && hasQuantityColumn) {
            dataQuality = 'good';
        } else if (dataPoints >= 14 && hasQuantityColumn) {
            dataQuality = 'fair';
        }

        // Detect patterns (simplified heuristics)
        const seasonalityDetected = dataPoints >= 30; // Assume seasonality possible with 30+ days
        const trendDetected = dataPoints >= 14; // Assume trend analysis possible with 14+ days
        
        // Determine volatility (simplified)
        const volatility: DataInsights['volatility'] = dataPoints < 30 ? 'high' : 'medium';

        // Generate warnings
        const warnings: string[] = [];
        if (dataPoints < 14) {
            warnings.push("Limited data may reduce forecast accuracy");
        }
        if (!hasDateColumn) {
            warnings.push("No date column detected - using row order for time sequence");
        }
        if (info.numeric_columns.length === 0) {
            warnings.push("No numeric columns found for forecasting");
        }

        // Generate recommendations
        const recommendations: string[] = [];
        if (dataPoints >= 90) {
            recommendations.push("Excellent data history - all forecasting methods available");
        }
        if (seasonalityDetected) {
            recommendations.push("Consider seasonal models for better accuracy");
        }
        if (dataPoints < 30) {
            recommendations.push("Consider simpler models due to limited data");
        }
        if (dataPoints >= 60) {
            recommendations.push("Machine learning models may capture complex patterns in your data");
        }

        // Recommend use case based on analysis
        let recommendedUseCase: keyof typeof USE_CASES = 'stable';
        if (dataPoints < 30) {
            recommendedUseCase = 'new_product';
        } else if (seasonalityDetected && dataPoints >= 60) {
            recommendedUseCase = 'seasonal';
        } else if (trendDetected && dataPoints >= 45) {
            recommendedUseCase = 'trending';
        } else if (dataPoints >= 90) {
            recommendedUseCase = 'fast_moving';
        } else if (dataPoints >= 60) {
            // Recommend ML model for moderate to large datasets
            recommendedUseCase = 'ml_model';
        }

        return {
            recommendedUseCase,
            dataQuality,
            seasonalityDetected,
            trendDetected,
            volatility,
            dataPoints,
            timeSpan,
            warnings,
            recommendations
        };
    };

    const handleConfigChange = (key: keyof ForecastConfig, value: any) => {
        const newConfig = { ...config, [key]: value };
        setConfig(newConfig);
        onConfigChange(newConfig);
    };

    const getDataQualityColor = (quality: DataInsights['dataQuality']) => {
        switch (quality) {
            case 'excellent': return 'text-green-600 bg-green-50 border-green-200';
            case 'good': return 'text-blue-600 bg-blue-50 border-blue-200';
            case 'fair': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
            case 'poor': return 'text-red-600 bg-red-50 border-red-200';
        }
    };

    if (!validationResult?.valid) {
        return (
            <Card className="border-gray-200">
                <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                        <Settings className="w-5 h-5" />
                        Forecast Settings
                    </CardTitle>
                </CardHeader>
                <CardContent>
                    <div className="flex items-center gap-2 text-gray-500">
                        <Info className="w-4 h-4" />
                        <span>Upload and validate your data to configure forecast settings</span>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <div className="space-y-6">
            {/* Data Insights */}
            {dataInsights && (
                <Card className="border-blue-100 bg-blue-50/30">
                    <CardHeader className="pb-3">
                        <CardTitle className="flex items-center gap-2 text-base text-blue-800">
                            <Info className="w-5 h-5" />
                            Smart Data Analysis
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="text-center">
                                <div className="text-2xl font-bold text-blue-600">{dataInsights.dataPoints}</div>
                                <div className="text-xs text-gray-600">Data Points</div>
                            </div>
                            <div className="text-center">
                                <div className={`text-sm font-medium px-2 py-1 rounded border ${getDataQualityColor(dataInsights.dataQuality)}`}>
                                    {dataInsights.dataQuality.toUpperCase()}
                                </div>
                                <div className="text-xs text-gray-600 mt-1">Data Quality</div>
                            </div>
                            <div className="text-center">
                                <div className="text-sm font-medium text-purple-600">
                                    {dataInsights.seasonalityDetected ? 'Detected' : 'Not Detected'}
                                </div>
                                <div className="text-xs text-gray-600">Seasonality</div>
                            </div>
                            <div className="text-center">
                                <div className="text-sm font-medium text-orange-600">
                                    {dataInsights.volatility.toUpperCase()}
                                </div>
                                <div className="text-xs text-gray-600">Volatility</div>
                            </div>
                        </div>

                        {dataInsights.recommendations.length > 0 && (
                            <div className="space-y-2">
                                <div className="text-sm font-medium text-blue-800">Recommendations:</div>
                                <ul className="text-sm text-blue-700 space-y-1">
                                    {dataInsights.recommendations.map((rec, idx) => (
                                        <li key={idx} className="flex items-start gap-2">
                                            <span className="text-blue-500 mt-0.5">•</span>
                                            {rec}
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Main Settings */}
            <Card>
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="flex items-center gap-2">
                            <Settings className="w-5 h-5" />
                            Forecast Configuration
                        </CardTitle>
                        <div className="flex items-center gap-2">
                            <Label htmlFor="advanced-mode" className="text-sm">Advanced Mode</Label>
                            <Switch
                                id="advanced-mode"
                                checked={isAdvancedMode}
                                onCheckedChange={setIsAdvancedMode}
                            />
                        </div>
                    </div>
                </CardHeader>
                <CardContent className="space-y-6">
                    {!isAdvancedMode ? (
                        // Simple Mode - Use Case Selection
                        <div className="space-y-4">
                            <div>
                                <Label className="text-base font-medium">What best describes your inventory?</Label>
                                <p className="text-sm text-gray-600 mb-3">
                                    We'll automatically configure the best forecasting approach for your use case.
                                </p>
                            </div>
                            
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {Object.entries(USE_CASES).map(([key, useCase]) => (
                                    <div
                                        key={key}
                                        className={`p-4 border rounded-lg cursor-pointer transition-all ${
                                            selectedUseCase === key
                                                ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-200'
                                                : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                        }`}
                                        onClick={() => setSelectedUseCase(key as keyof typeof USE_CASES)}
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className={`p-2 rounded ${
                                                selectedUseCase === key ? 'bg-blue-100 text-blue-600' : 'bg-gray-100 text-gray-600'
                                            }`}>
                                                {useCase.icon}
                                            </div>
                                            <div className="flex-1">
                                                <div className="font-medium text-sm">{useCase.label}</div>
                                                <div className="text-xs text-gray-600 mt-1">{useCase.description}</div>
                                                {selectedUseCase === key && (
                                                    <div className="text-xs text-blue-600 mt-2 font-medium">
                                                        ✓ Selected - {useCase.horizon} day forecast
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {dataInsights && selectedUseCase === dataInsights.recommendedUseCase && (
                                <div className="flex items-center gap-2 text-sm text-green-600 bg-green-50 p-3 rounded-lg border border-green-200">
                                    <Target className="w-4 h-4" />
                                    <span>Recommended based on your data analysis</span>
                                </div>
                            )}
                        </div>
                    ) : (
                        // Advanced Mode - Detailed Configuration
                        <div className="space-y-6">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                {/* Model Selection */}
                                <div className="space-y-2">
                                    <Label>Forecasting Model</Label>
                                    <Select
                                        value={config.model}
                                        onValueChange={(value) => handleConfigChange('model', value)}
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="AutoARIMA">Auto ARIMA (Recommended)</SelectItem>
                                            <SelectItem value="AutoETS">Auto ETS (Seasonal)</SelectItem>
                                            <SelectItem value="SeasonalNaive">Seasonal Naive (Simple)</SelectItem>
                                            <SelectItem value="Naive">Naive (Basic)</SelectItem>
                                            <SelectItem value="RandomWalkWithDrift">Random Walk (Trending)</SelectItem>
                                            <SelectItem value="SklearnModel">Machine Learning (Sklearn)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                {/* Forecast Horizon */}
                                <div className="space-y-2">
                                    <Label>Forecast Horizon (Days)</Label>
                                    <div className="space-y-2">
                                        <Slider
                                            value={[config.horizon || 30]}
                                            onValueChange={([value]: number[]) => handleConfigChange('horizon', value)}
                                            min={7}
                                            max={365}
                                            step={7}
                                            className="w-full"
                                        />
                                        <div className="flex justify-between text-xs text-gray-500">
                                            <span>7 days</span>
                                            <span className="font-medium">{config.horizon} days</span>
                                            <span>365 days</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Confidence Level */}
                                <div className="space-y-2">
                                    <Label>Confidence Level</Label>
                                    <div className="space-y-2">
                                        <Slider
                                            value={[config.confidence_level ? config.confidence_level * 100 : 95]}
                                            onValueChange={([value]: number[]) => handleConfigChange('confidence_level', value / 100)}
                                            min={80}
                                            max={99}
                                            step={1}
                                            className="w-full"
                                        />
                                        <div className="flex justify-between text-xs text-gray-500">
                                            <span>80%</span>
                                            <span className="font-medium">{Math.round((config.confidence_level || 0.95) * 100)}%</span>
                                            <span>99%</span>
                                        </div>
                                    </div>
                                </div>

                                {/* Seasonal Length */}
                                <div className="space-y-2">
                                    <Label>Seasonal Pattern (Days)</Label>
                                    <Select
                                        value={config.seasonal_length?.toString() || "none"}
                                        onValueChange={(value) => 
                                            handleConfigChange('seasonal_length', value === "none" ? null : parseInt(value))
                                        }
                                    >
                                        <SelectTrigger>
                                            <SelectValue />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="none">No Seasonality</SelectItem>
                                            <SelectItem value="7">Weekly (7 days)</SelectItem>
                                            <SelectItem value="30">Monthly (30 days)</SelectItem>
                                            <SelectItem value="90">Quarterly (90 days)</SelectItem>
                                            <SelectItem value="365">Yearly (365 days)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            {/* Advanced Warnings */}
                            {dataInsights?.warnings && dataInsights.warnings.length > 0 && (
                                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
                                    <div className="flex items-center gap-2 mb-2">
                                        <AlertTriangle className="w-4 h-4 text-yellow-500" />
                                        <span className="font-medium text-yellow-800">Configuration Warnings</span>
                                    </div>
                                    <ul className="text-sm text-yellow-700 space-y-1">
                                        {dataInsights.warnings.map((warning, idx) => (
                                            <li key={idx}>• {warning}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Configuration Summary */}
                    <div className="border-t pt-4 space-y-4">
                        <div className="flex items-center gap-2 mb-3">
                            <HelpCircle className="w-4 h-4 text-gray-500" />
                            <span className="text-sm font-medium text-gray-700">Current Configuration</span>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                                <span className="text-gray-500">Model:</span>
                                <div className="font-medium">{config.model}</div>
                            </div>
                            <div>
                                <span className="text-gray-500">Horizon:</span>
                                <div className="font-medium">{config.horizon} days</div>
                            </div>
                            <div>
                                <span className="text-gray-500">Confidence:</span>
                                <div className="font-medium">{Math.round((config.confidence_level || 0.95) * 100)}%</div>
                            </div>
                            <div>
                                <span className="text-gray-500">Seasonality:</span>
                                <div className="font-medium">
                                    {config.seasonal_length ? `${config.seasonal_length} days` : 'None'}
                                </div>
                            </div>
                        </div>
                        
                        {/* Submit Button */}
                        {onSubmit && (
                            <div className="flex justify-center pt-2">
                                <Button 
                                    onClick={onSubmit}
                                    disabled={isSubmitting}
                                    size="lg"
                                    className="px-8"
                                >
                                    {isSubmitting ? "Creating Forecast..." : "Create Forecast"}
                                </Button>
                            </div>
                        )}
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
