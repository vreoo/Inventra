import logging
from typing import List, Optional, Dict, Any

from models.external_factors import (
    ExternalFactorConfig, FactorAttribution, EnhancedForecastResult
)

# Import Ollama service
from services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

class AIAnalysisService:
    """Service for AI-powered analysis and insights generation using Ollama"""

    def __init__(self, config: ExternalFactorConfig):
        self.config = config
        self.ollama_service = None
        self.enabled = config.ai_analysis_enabled

        # Initialize Ollama service only
        if self.enabled:
            self.ollama_service = OllamaService()
            if self.ollama_service.enabled:
                logger.info("✅ AI Analysis Service initialized with Ollama")
            else:
                logger.warning("❌ Ollama not available - AI analysis disabled")
                self.enabled = False
        else:
            logger.info("ℹ️ AI analysis disabled by configuration")

        # Log final service status
        if self.enabled:
            logger.info("🚀 AI Analysis Service ready with Ollama")
        else:
            logger.warning("⚠️ AI Analysis Service is disabled - all AI features will use fallback responses")
    
    async def explain_trend(self, trend_data: Dict[str, Any]) -> Optional[str]:
        """Generate AI explanation of forecast trends"""
        if not self.enabled or not self.ollama_service:
            return self._fallback_trend_explanation(trend_data)

        try:
            return await self.ollama_service.explain_trend(trend_data)
        except Exception as e:
            logger.error(f"Error generating trend explanation: {str(e)}")
            return self._fallback_trend_explanation(trend_data)
    
    async def summarize_factors(self, factor_data: Dict[str, Any]) -> Optional[str]:
        """Generate AI summary of external factor impacts"""
        if not self.enabled or not self.ollama_service:
            return self._fallback_factor_summary(factor_data)

        try:
            return await self.ollama_service.summarize_factors(factor_data)
        except Exception as e:
            logger.error(f"Error generating factor summary: {str(e)}")
            return self._fallback_factor_summary(factor_data)
    
    async def generate_recommendations(self, forecast_data: Dict[str, Any]) -> List[str]:
        """Generate AI-powered actionable recommendations"""
        if not self.enabled or not self.ollama_service:
            return self._fallback_recommendations(forecast_data)

        try:
            return await self.ollama_service.generate_recommendations(forecast_data)
        except Exception as e:
            logger.error(f"Error generating recommendations: {str(e)}")
            return self._fallback_recommendations(forecast_data)
    
    async def assess_risks(self, risk_data: Dict[str, Any]) -> Optional[str]:
        """Generate AI assessment of forecast risks"""
        if not self.enabled or not self.ollama_service:
            return self._fallback_risk_assessment(risk_data)

        try:
            return await self.ollama_service.assess_risks(risk_data)
        except Exception as e:
            logger.error(f"Error generating risk assessment: {str(e)}")
            return self._fallback_risk_assessment(risk_data)
    

    
    # Fallback methods for when AI is not available
    
    def _fallback_trend_explanation(self, trend_data: Dict[str, Any]) -> str:
        """Fallback trend explanation without AI"""
        trend_direction = trend_data.get('trend_direction', 'stable')
        trend_percentage = trend_data.get('trend_percentage', 0)
        
        if trend_direction == 'increasing':
            return f"Inventory demand is trending upward by {trend_percentage:.1f}%, indicating growing market demand."
        elif trend_direction == 'decreasing':
            return f"Inventory demand is declining by {trend_percentage:.1f}%, suggesting reduced market activity."
        else:
            return "Inventory demand remains relatively stable with no significant trend changes."
    
    def _fallback_factor_summary(self, factor_data: Dict[str, Any]) -> str:
        """Fallback factor summary without AI"""
        weather_correlation = factor_data.get('weather_correlation', 0)
        holiday_impact = factor_data.get('holiday_impact', 0)
        
        if weather_correlation > 0.5:
            return f"Weather patterns show strong correlation ({weather_correlation:.1%}) with demand. Holiday effects add {holiday_impact:+.1%} seasonal variation."
        elif holiday_impact > 0.1:
            return f"Holiday seasonality is the primary external factor, contributing {holiday_impact:+.1%} demand variation."
        else:
            return "External factors show minimal impact on demand patterns. Forecasts rely primarily on historical trends."
    
    def _fallback_recommendations(self, forecast_data: Dict[str, Any]) -> List[str]:
        """Fallback recommendations without AI"""
        predicted_demand = forecast_data.get('predicted_demand', 0)
        current_stock = forecast_data.get('current_stock', 0)
        
        recommendations = []
        
        if current_stock < predicted_demand * 0.8:
            recommendations.append("Consider increasing inventory levels to meet predicted demand")
        
        if current_stock > predicted_demand * 1.5:
            recommendations.append("Current stock levels appear high - monitor for overstock situation")
        
        recommendations.append("Review forecast accuracy regularly and adjust inventory policies as needed")
        
        return recommendations[:3]  # Limit to 3 recommendations
    
    def _fallback_risk_assessment(self, risk_data: Dict[str, Any]) -> str:
        """Fallback risk assessment without AI"""
        confidence_level = risk_data.get('confidence_level', 0.8)
        data_quality = risk_data.get('data_quality', 0.9)
        forecast_horizon = risk_data.get('forecast_horizon', 30)
        
        if confidence_level > 0.8 and data_quality > 0.8:
            return f"High confidence forecast with good data quality. Reliable for {forecast_horizon}-day planning horizon."
        elif confidence_level > 0.6:
            return f"Moderate confidence forecast. Consider additional validation for decisions beyond {forecast_horizon//2} days."
        else:
            return f"Lower confidence forecast due to data limitations. Use with caution for strategic planning."
