"use client";

import { AIAnalysis } from "@/services/api";
import { Card, CardContent } from "@/components/ui/card";

interface AIAnalysisProps {
    analysis: AIAnalysis;
    dataQualityScore?: number;
}

export function AIAnalysisComponent({ analysis, dataQualityScore }: AIAnalysisProps) {
    const getConfidenceColor = (score: number) => {
        if (score >= 0.8) return "text-green-600 bg-green-50";
        if (score >= 0.6) return "text-yellow-600 bg-yellow-50";
        return "text-red-600 bg-red-50";
    };

    const getQualityColor = (score: number) => {
        if (score >= 0.8) return "text-green-600";
        if (score >= 0.6) return "text-yellow-600";
        return "text-red-600";
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">AI-Powered Analysis</h3>
                <div className="flex items-center gap-4">
                    {dataQualityScore !== undefined && (
                        <div className="text-sm">
                            <span className="text-gray-600">Data Quality: </span>
                            <span className={`font-semibold ${getQualityColor(dataQualityScore)}`}>
                                {(dataQualityScore * 100).toFixed(0)}%
                            </span>
                        </div>
                    )}
                    <div className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${getConfidenceColor(analysis.confidence_score)}`}>
                        <span className="w-2 h-2 bg-current rounded-full mr-2"></span>
                        {(analysis.confidence_score * 100).toFixed(0)}% Confidence
                    </div>
                </div>
            </div>

            {/* Trend Explanation */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                            <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <h4 className="font-medium text-gray-900 mb-2">Trend Analysis</h4>
                            <p className="text-gray-700 leading-relaxed">{analysis.trend_explanation}</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Factor Summary */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                            <svg className="w-4 h-4 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <h4 className="font-medium text-gray-900 mb-2">External Factors Impact</h4>
                            <p className="text-gray-700 leading-relaxed">{analysis.factor_summary}</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Recommendations */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center">
                            <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <h4 className="font-medium text-gray-900 mb-3">Strategic Recommendations</h4>
                            <div className="space-y-2">
                                {analysis.recommendations.map((recommendation, index) => (
                                    <div key={index} className="flex items-start gap-2">
                                        <div className="flex-shrink-0 w-1.5 h-1.5 bg-green-500 rounded-full mt-2"></div>
                                        <p className="text-gray-700 leading-relaxed">{recommendation}</p>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* Risk Assessment */}
            <Card>
                <CardContent className="p-4">
                    <div className="flex items-start gap-3">
                        <div className="flex-shrink-0 w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center">
                            <svg className="w-4 h-4 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <h4 className="font-medium text-gray-900 mb-2">Risk Assessment</h4>
                            <p className="text-gray-700 leading-relaxed">{analysis.risk_assessment}</p>
                        </div>
                    </div>
                </CardContent>
            </Card>

            {/* AI Disclaimer */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                    <div className="flex-shrink-0">
                        <svg className="w-5 h-5 text-blue-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                    </div>
                    <div className="text-sm text-blue-800">
                        <p className="font-medium mb-1">AI-Generated Insights</p>
                        <p>This analysis is generated by AI and should be used as guidance alongside your business expertise. Always validate recommendations with your domain knowledge and current market conditions.</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
