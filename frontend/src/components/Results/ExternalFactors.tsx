"use client";

import { WeatherData, HolidayData, FactorAttribution } from "@/services/api";
import { Card, CardContent } from "@/components/ui/card";

interface ExternalFactorsProps {
    weatherData?: WeatherData[];
    holidayData?: HolidayData[];
    factorAttributions?: FactorAttribution[];
}

export function ExternalFactors({ weatherData, holidayData, factorAttributions }: ExternalFactorsProps) {
    if (!weatherData && !holidayData && !factorAttributions) {
        return null;
    }

    return (
        <div className="space-y-6">
            <h3 className="text-lg font-semibold text-white">External Factors Analysis</h3>
            
            {/* Factor Attributions */}
            {factorAttributions && factorAttributions.length > 0 && (
                <Card className="border-white/10 bg-white/5 text-slate-100">
                    <CardContent className="p-4">
                        <h4 className="mb-3 font-medium text-white">Impact Analysis</h4>
                        <div className="space-y-3">
                            {factorAttributions.map((factor, index) => (
                                <div key={index} className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-900/60 p-3">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                factor.factor_type === "weather" ? "bg-cyan-500/15 text-cyan-100 border border-cyan-400/30" :
                                                factor.factor_type === "holiday" ? "bg-indigo-500/15 text-indigo-100 border border-indigo-400/30" :
                                                factor.factor_type === "seasonal" ? "bg-emerald-500/15 text-emerald-100 border border-emerald-400/30" :
                                                "bg-amber-500/15 text-amber-100 border border-amber-400/30"
                                            }`}>
                                                {factor.factor_type}
                                            </span>
                                            <span className="font-medium text-white">{factor.factor_name}</span>
                                        </div>
                                        <p className="text-sm text-slate-200">{factor.description}</p>
                                    </div>
                                    <div className="text-right ml-4">
                                        <div className="text-lg font-semibold text-white">
                                            {factor.impact_score > 0 ? '+' : ''}{(factor.impact_score * 100).toFixed(1)}%
                                        </div>
                                        <div className="text-xs text-slate-400">
                                            {(factor.confidence * 100).toFixed(0)}% confidence
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}

            {/* Weather Data */}
            {weatherData && weatherData.length > 0 && (
                <Card className="border-white/10 bg-white/5 text-slate-100">
                    <CardContent className="p-4">
                        <h4 className="mb-3 font-medium text-white">Weather Conditions</h4>
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="border-b border-white/10 text-left text-slate-300">
                                        <th className="px-3 py-2 font-medium">Date</th>
                                        <th className="px-3 py-2 font-medium">Condition</th>
                                        <th className="px-3 py-2 font-medium">Temp (°C)</th>
                                        <th className="px-3 py-2 font-medium">Humidity</th>
                                        <th className="px-3 py-2 font-medium">Precipitation</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-white/5">
                                    {weatherData.slice(0, 7).map((weather, index) => (
                                        <tr key={index} className="hover:bg-white/5">
                                            <td className="px-3 py-2 text-slate-100">{weather.date}</td>
                                            <td className="py-2 px-3">
                                                <span className="inline-flex items-center gap-2 text-slate-200">
                                                    <span className={`w-2 h-2 rounded-full ${
                                                        weather.weather_condition.toLowerCase().includes('rain') ? 'bg-blue-500' :
                                                        weather.weather_condition.toLowerCase().includes('sun') ? 'bg-yellow-500' :
                                                        weather.weather_condition.toLowerCase().includes('cloud') ? 'bg-gray-500' :
                                                        'bg-gray-400'
                                                    }`}></span>
                                                    <span>{weather.weather_condition}</span>
                                                </span>
                                            </td>
                                            <td className="px-3 py-2 font-mono text-slate-100">{weather.temperature.toFixed(1)}</td>
                                            <td className="px-3 py-2 font-mono text-slate-300">{weather.humidity.toFixed(0)}%</td>
                                            <td className="px-3 py-2 font-mono text-slate-300">{weather.precipitation.toFixed(1)}mm</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {weatherData.length > 7 && (
                            <p className="mt-2 text-xs text-slate-400">
                                Showing first 7 days of {weatherData.length} total weather records
                            </p>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Holiday Data */}
            {holidayData && holidayData.length > 0 && (
                <Card className="border-white/10 bg-white/5 text-slate-100">
                    <CardContent className="p-4">
                        <h4 className="mb-3 font-medium text-white">Holidays & Events</h4>
                        <div className="space-y-2">
                            {holidayData.map((holiday, index) => (
                                <div key={index} className="flex items-center justify-between rounded-lg border border-white/10 bg-slate-900/60 p-3">
                                    <div className="flex items-center gap-3">
                                        <div className="text-sm font-medium text-white">{holiday.date}</div>
                                        <div>
                                            <div className="font-medium text-white">{holiday.name}</div>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                    holiday.type === "national" ? "bg-rose-500/15 text-rose-100 border border-rose-400/30" :
                                                    holiday.type === "regional" ? "bg-blue-500/15 text-blue-100 border border-blue-400/30" :
                                                    holiday.type === "religious" ? "bg-indigo-500/15 text-indigo-100 border border-indigo-400/30" :
                                                    "bg-emerald-500/15 text-emerald-100 border border-emerald-400/30"
                                                }`}>
                                                    {holiday.type}
                                                </span>
                                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                    holiday.impact_level === "high" ? "bg-rose-500/15 text-rose-100 border border-rose-400/30" :
                                                    holiday.impact_level === "medium" ? "bg-amber-500/15 text-amber-100 border border-amber-400/30" :
                                                    "bg-emerald-500/15 text-emerald-100 border border-emerald-400/30"
                                                }`}>
                                                    {holiday.impact_level} impact
                                                </span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            )}
        </div>
    );
}
