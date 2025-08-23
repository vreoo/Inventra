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
            <h3 className="text-lg font-semibold text-gray-900">External Factors Analysis</h3>
            
            {/* Factor Attributions */}
            {factorAttributions && factorAttributions.length > 0 && (
                <Card>
                    <CardContent className="p-4">
                        <h4 className="font-medium mb-3 text-gray-800">Impact Analysis</h4>
                        <div className="space-y-3">
                            {factorAttributions.map((factor, index) => (
                                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                factor.factor_type === "weather" ? "bg-blue-100 text-blue-800" :
                                                factor.factor_type === "holiday" ? "bg-purple-100 text-purple-800" :
                                                factor.factor_type === "seasonal" ? "bg-green-100 text-green-800" :
                                                "bg-orange-100 text-orange-800"
                                            }`}>
                                                {factor.factor_type}
                                            </span>
                                            <span className="font-medium text-gray-900">{factor.factor_name}</span>
                                        </div>
                                        <p className="text-sm text-gray-600">{factor.description}</p>
                                    </div>
                                    <div className="text-right ml-4">
                                        <div className="text-lg font-semibold text-gray-900">
                                            {factor.impact_score > 0 ? '+' : ''}{(factor.impact_score * 100).toFixed(1)}%
                                        </div>
                                        <div className="text-xs text-gray-500">
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
                <Card>
                    <CardContent className="p-4">
                        <h4 className="font-medium mb-3 text-gray-800">Weather Conditions</h4>
                        <div className="overflow-x-auto">
                            <table className="min-w-full text-sm">
                                <thead>
                                    <tr className="border-b border-gray-200">
                                        <th className="text-left py-2 px-3 font-medium text-gray-700">Date</th>
                                        <th className="text-left py-2 px-3 font-medium text-gray-700">Condition</th>
                                        <th className="text-left py-2 px-3 font-medium text-gray-700">Temp (°C)</th>
                                        <th className="text-left py-2 px-3 font-medium text-gray-700">Humidity</th>
                                        <th className="text-left py-2 px-3 font-medium text-gray-700">Precipitation</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {weatherData.slice(0, 7).map((weather, index) => (
                                        <tr key={index} className="border-b border-gray-100">
                                            <td className="py-2 px-3 text-gray-900">{weather.date}</td>
                                            <td className="py-2 px-3">
                                                <span className="inline-flex items-center gap-1">
                                                    <span className={`w-2 h-2 rounded-full ${
                                                        weather.weather_condition.toLowerCase().includes('rain') ? 'bg-blue-500' :
                                                        weather.weather_condition.toLowerCase().includes('sun') ? 'bg-yellow-500' :
                                                        weather.weather_condition.toLowerCase().includes('cloud') ? 'bg-gray-500' :
                                                        'bg-gray-400'
                                                    }`}></span>
                                                    <span className="text-gray-700">{weather.weather_condition}</span>
                                                </span>
                                            </td>
                                            <td className="py-2 px-3 font-mono text-gray-900">{weather.temperature.toFixed(1)}</td>
                                            <td className="py-2 px-3 font-mono text-gray-700">{weather.humidity.toFixed(0)}%</td>
                                            <td className="py-2 px-3 font-mono text-gray-700">{weather.precipitation.toFixed(1)}mm</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                        {weatherData.length > 7 && (
                            <p className="text-xs text-gray-500 mt-2">
                                Showing first 7 days of {weatherData.length} total weather records
                            </p>
                        )}
                    </CardContent>
                </Card>
            )}

            {/* Holiday Data */}
            {holidayData && holidayData.length > 0 && (
                <Card>
                    <CardContent className="p-4">
                        <h4 className="font-medium mb-3 text-gray-800">Holidays & Events</h4>
                        <div className="space-y-2">
                            {holidayData.map((holiday, index) => (
                                <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                                    <div className="flex items-center gap-3">
                                        <div className="text-sm font-medium text-gray-900">{holiday.date}</div>
                                        <div>
                                            <div className="font-medium text-gray-900">{holiday.name}</div>
                                            <div className="flex items-center gap-2 mt-1">
                                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                    holiday.type === "national" ? "bg-red-100 text-red-800" :
                                                    holiday.type === "regional" ? "bg-blue-100 text-blue-800" :
                                                    holiday.type === "religious" ? "bg-purple-100 text-purple-800" :
                                                    "bg-green-100 text-green-800"
                                                }`}>
                                                    {holiday.type}
                                                </span>
                                                <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${
                                                    holiday.impact_level === "high" ? "bg-red-100 text-red-800" :
                                                    holiday.impact_level === "medium" ? "bg-yellow-100 text-yellow-800" :
                                                    "bg-green-100 text-green-800"
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
