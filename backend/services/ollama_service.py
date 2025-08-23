import asyncio
import logging
import aiohttp
from typing import Optional, Dict, Any
import os

logger = logging.getLogger(__name__)

class OllamaService:
    """Service for Ollama-powered analysis and insights generation"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = os.getenv("OLLAMA_BASE_URL", base_url)
        self.model = os.getenv("OLLAMA_MODEL", "phi:2.7b")  # Use correct model name
        self.enabled = True
        self._connection_timeout = 10  # seconds
        self._max_retries = 3
        self._retry_delay = 1  # seconds
        self._check_availability()

    def _check_availability(self):
        """Check if Ollama is available and has the required model"""
        try:
            logger.info(f"Checking Ollama availability at {self.base_url}")

            # Handle both sync and async contexts
            try:
                # Try to get the current event loop
                loop = asyncio.get_running_loop()
                # If we're already in an event loop, we can't use asyncio.run()
                # Instead, we'll defer the check and assume it's available for now
                logger.info("Running in existing event loop - deferring availability check")
                self.enabled = True  # Assume available for now, will check when actually used
            except RuntimeError:
                # No event loop running, we can use asyncio.run()
                self.enabled = asyncio.run(self._async_check_availability())

            if self.enabled:
                logger.info(f"✅ Ollama service initialized successfully with model: {self.model}")
            else:
                logger.warning(f"❌ Ollama service unavailable - will fallback to other AI services")
        except Exception as e:
            logger.error(f"❌ Error during Ollama availability check: {str(e)}")
            self.enabled = False

    async def _async_check_availability(self) -> bool:
        """Asynchronously check if Ollama service is available"""
        try:
            # Check if Ollama API is responding
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self._connection_timeout)) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status != 200:
                        logger.warning(f"Ollama API returned status {response.status}")
                        return False

                    data = await response.json()
                    models = [model['name'] for model in data.get('models', [])]

                    if self.model not in models:
                        logger.warning(f"Required model '{self.model}' not found. Available models: {models}")
                        return False

                    logger.info(f"Found required model '{self.model}' in available models: {models}")
                    return True

        except asyncio.TimeoutError:
            logger.error(f"Ollama connection timeout after {self._connection_timeout} seconds")
            return False
        except aiohttp.ClientError as e:
            logger.error(f"Ollama connection error: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error checking Ollama availability: {str(e)}")
            return False

    async def is_available(self) -> bool:
        """Check if Ollama service is actually available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/tags", timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = [model['name'] for model in data.get('models', [])]
                        return self.model in models
                    return False
        except Exception as e:
            logger.error(f"Error checking Ollama availability: {str(e)}")
            return False

    async def generate_response(self, prompt: str, max_tokens: int = 150) -> str:
        """Generate response using Ollama with retry logic"""
        if not self.enabled:
            raise Exception("Ollama service is not enabled")

        last_exception = None

        # Retry logic with exponential backoff
        for attempt in range(self._max_retries):
            try:
                # Ensure Ollama is available
                if not await self.is_available():
                    raise Exception(f"Ollama model '{self.model}' is not available")

                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                }

                timeout = aiohttp.ClientTimeout(total=30, connect=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(
                        f"{self.base_url}/api/generate",
                        json=payload
                    ) as response:
                        if response.status == 200:
                            data = await response.json()
                            response_text = data.get('response', '').strip()
                            if response_text:
                                return response_text
                            else:
                                raise Exception("Ollama returned empty response")
                        else:
                            error_text = await response.text()
                            logger.warning(f"Ollama API error (attempt {attempt + 1}): Status {response.status}, Error: {error_text}")
                            raise Exception(f"Ollama API error: {error_text}")

            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"Ollama timeout on attempt {attempt + 1}/{self._max_retries}: {str(e)}")
            except aiohttp.ClientError as e:
                last_exception = e
                logger.warning(f"Ollama connection error on attempt {attempt + 1}/{self._max_retries}: {str(e)}")
            except Exception as e:
                last_exception = e
                logger.warning(f"Ollama generation error on attempt {attempt + 1}/{self._max_retries}: {str(e)}")

            # Wait before retry (exponential backoff)
            if attempt < self._max_retries - 1:
                wait_time = self._retry_delay * (2 ** attempt)
                logger.info(f"Retrying Ollama request in {wait_time} seconds...")
                await asyncio.sleep(wait_time)

        # All retries failed
        error_msg = f"Ollama generation failed after {self._max_retries} attempts"
        if last_exception:
            error_msg += f": {str(last_exception)}"
        logger.error(error_msg)
        raise Exception(error_msg)

    async def explain_trend(self, trend_data: Dict[str, Any]) -> Optional[str]:
        """Generate Ollama explanation of forecast trends"""
        try:
            prompt = self._build_trend_prompt(trend_data)
            return await self.generate_response(prompt, max_tokens=150)
        except Exception as e:
            logger.error(f"Error generating trend explanation with Ollama: {str(e)}")
            return None

    async def summarize_factors(self, factor_data: Dict[str, Any]) -> Optional[str]:
        """Generate Ollama summary of external factor impacts"""
        try:
            prompt = self._build_factor_prompt(factor_data)
            return await self.generate_response(prompt, max_tokens=200)
        except Exception as e:
            logger.error(f"Error generating factor summary with Ollama: {str(e)}")
            return None

    async def generate_recommendations(self, forecast_data: Dict[str, Any]) -> list[str]:
        """Generate Ollama-powered actionable recommendations"""
        try:
            prompt = self._build_recommendations_prompt(forecast_data)
            response = await self.generate_response(prompt, max_tokens=250)
            logger.info(f"Ollama recommendations response: {response}")
            return self._parse_recommendations(response)
        except Exception as e:
            logger.error(f"Error generating recommendations with Ollama: {str(e)}")
            return []

    async def assess_risks(self, risk_data: Dict[str, Any]) -> Optional[str]:
        """Generate Ollama assessment of forecast risks"""
        try:
            prompt = self._build_risk_prompt(risk_data)
            return await self.generate_response(prompt, max_tokens=180)
        except Exception as e:
            logger.error(f"Error generating risk assessment with Ollama: {str(e)}")
            return None

    def _build_trend_prompt(self, trend_data: Dict[str, Any]) -> str:
        """Build prompt for trend explanation"""
        trend_direction = trend_data.get('trend_direction', 'stable')
        trend_percentage = trend_data.get('trend_percentage', 0)
        key_factors = trend_data.get('key_factors', [])
        time_period = trend_data.get('time_period', '30 days')

        factors_text = ', '.join(key_factors) if key_factors else 'seasonal patterns'

        return f"""
        Explain this inventory trend in simple business terms:
        - Current trend: {trend_direction} ({trend_percentage:+.1f}%)
        - Key factors: {factors_text}
        - Time period: {time_period}

        Provide a 1-2 sentence explanation that a business manager would understand.
        """

    def _build_factor_prompt(self, factor_data: Dict[str, Any]) -> str:
        """Build prompt for factor impact summary"""
        weather_correlation = factor_data.get('weather_correlation', 0)
        holiday_impact = factor_data.get('holiday_impact', 0)
        other_factors = factor_data.get('other_factors', [])

        other_text = ', '.join(other_factors) if other_factors else 'none identified'

        return f"""
        Summarize the impact of external factors on inventory predictions:
        - Weather correlation: {weather_correlation:.1%}
        - Holiday impact: {holiday_impact:+.1%}
        - Other factors: {other_text}

        Explain which factors matter most and why in 2-3 sentences.
        """

    def _build_recommendations_prompt(self, forecast_data: Dict[str, Any]) -> str:
        """Build prompt for recommendations"""
        predicted_demand = forecast_data.get('predicted_demand', 0)
        current_stock = forecast_data.get('current_stock', 0)
        risk_factors = forecast_data.get('risk_factors', [])
        external_factors = forecast_data.get('external_factors', [])

        risk_text = ', '.join(risk_factors) if risk_factors else 'none identified'
        external_text = ', '.join(external_factors) if external_factors else 'none'

        return f"""
        Generate specific inventory recommendations based on:
        - Predicted demand: {predicted_demand}
        - Current stock: {current_stock}
        - Risk factors: {risk_text}
        - External factors: {external_text}

        Provide 2-3 specific, actionable recommendations. Format as numbered list.
        """

    def _build_risk_prompt(self, risk_data: Dict[str, Any]) -> str:
        """Build prompt for risk assessment"""
        confidence_level = risk_data.get('confidence_level', 0.8)
        data_quality = risk_data.get('data_quality', 0.9)
        forecast_horizon = risk_data.get('forecast_horizon', 30)

        return f"""
        Assess the reliability of this inventory forecast:
        - Model confidence: {confidence_level:.1%}
        - Data quality: {data_quality:.1%}
        - Forecast horizon: {forecast_horizon} days

        Provide a brief risk assessment in business terms (2-3 sentences).
        """

    def _parse_recommendations(self, response: str) -> list[str]:
        """Parse recommendations from Ollama response"""
        try:
            # Split by numbered list items
            lines = response.strip().split('\n')
            recommendations = []

            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove numbering/bullets and clean up
                    clean_line = line.lstrip('0123456789.-• ').strip()
                    if clean_line:
                        recommendations.append(clean_line)

            return recommendations[:3]  # Limit to 3 recommendations

        except Exception as e:
            logger.error(f"Error parsing Ollama recommendations: {str(e)}")
            return [response] if response else []
