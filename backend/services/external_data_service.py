import asyncio
import aiohttp
import logging
import math
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from cachetools import TTLCache
import holidays
import json
import os
from dataclasses import dataclass

# Try to import numpy, fallback to math if not available
try:
    import numpy as np
except ImportError:
    np = None

from models.external_factors import (
    WeatherData, HolidayData, EventData, ExternalFactorRequest,
    ExternalFactorSummary, WeatherCondition, HolidayType, EventType,
    DataQualityMetrics, ExternalFactorConfig
)

logger = logging.getLogger(__name__)

@dataclass
class APIUsageStats:
    """Track API usage for cost monitoring"""
    daily_calls: int = 0
    monthly_calls: int = 0
    daily_cost: float = 0.0
    monthly_cost: float = 0.0
    last_reset_date: Optional[date] = None

class WeatherDataProvider:
    """Provider for weather data using Visual Crossing API"""

    def __init__(self, api_key: str, cache_ttl: int = 3600):
        self.api_key = api_key
        self.base_url = "https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline"
        self.cache = TTLCache(maxsize=1000, ttl=cache_ttl)
        self.usage_stats = APIUsageStats()
        self.cost_per_call = 0.0  # Visual Crossing has a free tier
        
    async def get_weather_data(self, location: str, start_date: date, end_date: date) -> List[WeatherData]:
        """Get historical weather data for a date range"""
        try:
            weather_data = []
            current_date = start_date
            
            while current_date <= end_date:
                # Check cache first
                cache_key = f"weather_{location}_{current_date.isoformat()}"
                if cache_key in self.cache:
                    weather_data.append(self.cache[cache_key])
                    current_date += timedelta(days=1)
                    continue
                
                # Get weather data from API
                weather_point = await self._fetch_historical_weather(location, current_date)
                if weather_point:
                    self.cache[cache_key] = weather_point
                    weather_data.append(weather_point)
                    self._update_usage_stats()
                
                current_date += timedelta(days=1)
                
                # Add small delay to respect rate limits
                await asyncio.sleep(0.1)
            
            logger.info(f"Retrieved {len(weather_data)} weather data points for {location}")
            return weather_data
            
        except Exception as e:
            logger.error(f"Error retrieving weather data: {str(e)}")
            return []
    
    async def get_weather_forecast(self, location: str, days: int) -> List[WeatherData]:
        """Get weather forecast for future dates"""
        try:
            cache_key = f"forecast_{location}_{days}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            forecast_data = await self._fetch_weather_forecast(location, days)
            if forecast_data:
                self.cache[cache_key] = forecast_data
                self._update_usage_stats()
            
            return forecast_data or []
            
        except Exception as e:
            logger.error(f"Error retrieving weather forecast: {str(e)}")
            return []
    
    async def _fetch_historical_weather(self, location: str, target_date: date) -> Optional[WeatherData]:
        """Fetch historical weather data for a specific date using Visual Crossing"""
        try:
            today = date.today()

            if target_date >= today:
                # For future dates, use forecast data
                logger.info(f"Using forecast data for future date {target_date}")
                return await self._fetch_weather_forecast_for_date(location, target_date)
            else:
                # For past dates, try to get historical data from Visual Crossing
                # Visual Crossing provides historical data in their free tier
                logger.info(f"Fetching historical weather data for {target_date}")
                return await self._fetch_visual_crossing_historical(location, target_date)

        except Exception as e:
            logger.error(f"Error fetching historical weather for {location} on {target_date}: {str(e)}")
            # Fallback to current weather approximation
            logger.info(f"Falling back to current weather approximation for {target_date}")
            return await self._fetch_current_weather_as_historical(location, target_date)

    async def _fetch_weather_forecast_for_date(self, location: str, target_date: date) -> Optional[WeatherData]:
        """Fetch weather forecast data for a specific future date"""
        try:
            # Get forecast data for the next few days
            forecast_data = await self._fetch_weather_forecast(location, 5)  # 5-day forecast

            # Find the data point for our target date
            for weather_point in forecast_data:
                if weather_point.date == target_date:
                    return weather_point

            # If exact date not found, return the first available forecast
            if forecast_data:
                logger.warning(f"Exact forecast date {target_date} not found, using closest available")
                return forecast_data[0]

            return None

        except Exception as e:
            logger.error(f"Error fetching forecast for date {target_date}: {str(e)}")
            return None

    async def _fetch_current_weather_as_historical(self, location: str, target_date: date) -> Optional[WeatherData]:
        """Use current weather as approximation for historical dates (fallback method)"""
        try:
            # Get current weather data using Visual Crossing API
            url = f"{self.base_url}/{location}/today"
            params = {
                'key': self.api_key,
                'unitGroup': 'metric',
                'include': 'current'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Create WeatherData using current weather but with target date
                        weather_data = self._parse_visual_crossing_current_weather(location, target_date, data)

                        # Add a note that this is approximated data
                        logger.info(f"Using current weather approximation for historical date {target_date}")

                        return weather_data
                    else:
                        logger.warning(f"Current weather API returned status {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching current weather as historical for {location} on {target_date}: {str(e)}")
            return None
    
    async def _fetch_weather_forecast(self, location: str, days: int) -> List[WeatherData]:
        """Fetch weather forecast data using Visual Crossing API"""
        try:
            # Use Visual Crossing API for forecast
            end_date = date.today() + timedelta(days=days)
            url = f"{self.base_url}/{location}/{date.today().isoformat()}/{end_date.isoformat()}"
            params = {
                'key': self.api_key,
                'unitGroup': 'metric',
                'include': 'days',
                'elements': 'datetime,tempmax,tempmin,temp,precip,humidity,windspeed,conditions'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_visual_crossing_forecast(location, data.get('days', []))
                    else:
                        logger.warning(f"Weather forecast API returned status {response.status}")
                        return []

        except Exception as e:
            logger.error(f"Error fetching weather forecast: {str(e)}")
            return []
    
    async def _get_coordinates(self, location: str) -> Tuple[float, float]:
        """Get coordinates for a location using Visual Crossing geocoding"""
        try:
            cache_key = f"coords_{location}"
            if cache_key in self.cache:
                return self.cache[cache_key]

            # For Visual Crossing, we can use the location string directly in the weather API
            # But we need to validate it first with a simple API call
            test_url = f"{self.base_url}/{location}/today"
            params = {
                'key': self.api_key,
                'unitGroup': 'metric',
                'include': 'current'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(test_url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and 'latitude' in data and 'longitude' in data:
                            coords = (data['latitude'], data['longitude'])
                            self.cache[cache_key] = coords
                            return coords
                    else:
                        logger.warning(f"Location validation failed for {location}: {response.status}")

            # Fallback coordinates (New York)
            return (40.7128, -74.0060)

        except Exception as e:
            logger.error(f"Error getting coordinates for {location}: {str(e)}")
            return (40.7128, -74.0060)  # Default to New York
    
    def _parse_weather_data(self, location: str, target_date: date, weather_json: Dict) -> WeatherData:
        """Parse weather data from API response"""
        try:
            # Map weather condition
            condition_map = {
                'clear': WeatherCondition.CLEAR,
                'clouds': WeatherCondition.CLOUDY,
                'rain': WeatherCondition.RAIN,
                'snow': WeatherCondition.SNOW,
                'thunderstorm': WeatherCondition.STORM,
                'mist': WeatherCondition.FOG,
                'fog': WeatherCondition.FOG
            }
            
            weather_main = weather_json.get('weather', [{}])[0].get('main', '').lower()
            weather_condition = condition_map.get(weather_main, WeatherCondition.CLEAR)
            
            # Calculate seasonal index (simplified)
            day_of_year = target_date.timetuple().tm_yday
            if np is not None:
                seasonal_index = round(np.sin(2 * np.pi * day_of_year / 365), 2)
            else:
                seasonal_index = round(math.sin(2 * math.pi * day_of_year / 365), 2)
            
            return WeatherData(
                location=location,
                date=target_date,
                temperature_avg=weather_json.get('temp'),
                temperature_min=weather_json.get('temp'),  # Historical data doesn't have min/max
                temperature_max=weather_json.get('temp'),
                precipitation=weather_json.get('rain', {}).get('1h', 0) + weather_json.get('snow', {}).get('1h', 0),
                humidity=weather_json.get('humidity'),
                wind_speed=weather_json.get('wind_speed'),
                weather_condition=weather_condition,
                seasonal_index=seasonal_index
            )
            
        except Exception as e:
            logger.error(f"Error parsing weather data: {str(e)}")
            return WeatherData(location=location, date=target_date)
    
    def _parse_forecast_data_free(self, location: str, forecast_json: List[Dict]) -> List[WeatherData]:
        """Parse forecast data from free tier 5-day forecast API"""
        try:
            forecast_data = []

            # Group by day (take first entry for each day)
            daily_forecasts = {}
            for entry in forecast_json:
                dt = datetime.fromtimestamp(entry['dt'])
                day_key = dt.date()

                if day_key not in daily_forecasts:
                    daily_forecasts[day_key] = entry

            for forecast_date, day_data in daily_forecasts.items():
                # Map weather condition
                condition_map = {
                    'clear': WeatherCondition.CLEAR,
                    'clouds': WeatherCondition.CLOUDY,
                    'rain': WeatherCondition.RAIN,
                    'snow': WeatherCondition.SNOW,
                    'thunderstorm': WeatherCondition.STORM,
                    'mist': WeatherCondition.FOG,
                    'fog': WeatherCondition.FOG
                }

                weather_main = day_data.get('weather', [{}])[0].get('main', '').lower()
                weather_condition = condition_map.get(weather_main, WeatherCondition.CLEAR)

                # Calculate seasonal index
                day_of_year = forecast_date.timetuple().tm_yday
                if np is not None:
                    seasonal_index = round(np.sin(2 * np.pi * day_of_year / 365), 2)
                else:
                    seasonal_index = round(math.sin(2 * math.pi * day_of_year / 365), 2)

                weather_point = WeatherData(
                    location=location,
                    date=forecast_date,
                    temperature_avg=day_data['main']['temp'],
                    temperature_min=day_data['main']['temp_min'],
                    temperature_max=day_data['main']['temp_max'],
                    precipitation=day_data.get('rain', {}).get('3h', 0),
                    humidity=day_data['main']['humidity'],
                    wind_speed=day_data['wind']['speed'],
                    weather_condition=weather_condition,
                    seasonal_index=seasonal_index
                )

                forecast_data.append(weather_point)

            return forecast_data

        except Exception as e:
            logger.error(f"Error parsing free tier forecast data: {str(e)}")
            return []

    def _parse_forecast_data(self, location: str, forecast_json: List[Dict]) -> List[WeatherData]:
        """Parse forecast data from API response (legacy method)"""
        try:
            forecast_data = []
            base_date = date.today()

            for i, day_data in enumerate(forecast_json):
                forecast_date = base_date + timedelta(days=i+1)

                # Map weather condition
                condition_map = {
                    'clear': WeatherCondition.CLEAR,
                    'clouds': WeatherCondition.CLOUDY,
                    'rain': WeatherCondition.RAIN,
                    'snow': WeatherCondition.SNOW,
                    'thunderstorm': WeatherCondition.STORM,
                    'mist': WeatherCondition.FOG,
                    'fog': WeatherCondition.FOG
                }

                weather_main = day_data.get('weather', [{}])[0].get('main', '').lower()
                weather_condition = condition_map.get(weather_main, WeatherCondition.CLEAR)

                # Calculate seasonal index
                day_of_year = forecast_date.timetuple().tm_yday
                if np is not None:
                    seasonal_index = round(np.sin(2 * np.pi * day_of_year / 365), 2)
                else:
                    seasonal_index = round(math.sin(2 * math.pi * day_of_year / 365), 2)

                weather_point = WeatherData(
                    location=location,
                    date=forecast_date,
                    temperature_avg=(day_data['temp']['min'] + day_data['temp']['max']) / 2,
                    temperature_min=day_data['temp']['min'],
                    temperature_max=day_data['temp']['max'],
                    precipitation=day_data.get('rain', {}).get('1h', 0) + day_data.get('snow', {}).get('1h', 0),
                    humidity=day_data.get('humidity'),
                    wind_speed=day_data.get('wind_speed'),
                    weather_condition=weather_condition,
                    seasonal_index=seasonal_index
                )

                forecast_data.append(weather_point)

            return forecast_data

        except Exception as e:
            logger.error(f"Error parsing forecast data: {str(e)}")
            return []
    
    def _update_usage_stats(self):
        """Update API usage statistics"""
        today = date.today()
        
        # Reset daily stats if new day
        if self.usage_stats.last_reset_date != today:
            self.usage_stats.daily_calls = 0
            self.usage_stats.daily_cost = 0.0
            self.usage_stats.last_reset_date = today
        
        self.usage_stats.daily_calls += 1
        self.usage_stats.monthly_calls += 1
        self.usage_stats.daily_cost += self.cost_per_call
        self.usage_stats.monthly_cost += self.cost_per_call

    async def _fetch_visual_crossing_historical(self, location: str, target_date: date) -> Optional[WeatherData]:
        """Fetch historical weather data from Visual Crossing API"""
        try:
            # Visual Crossing API allows historical data queries
            # Format: location/date
            url = f"{self.base_url}/{location}/{target_date.isoformat()}"
            params = {
                'key': self.api_key,
                'unitGroup': 'metric',
                'include': 'days',
                'elements': 'datetime,tempmax,tempmin,temp,precip,humidity,windspeed,conditions'
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=30) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_visual_crossing_historical(location, target_date, data)
                    else:
                        logger.warning(f"Historical weather API returned status {response.status}")
                        return None

        except Exception as e:
            logger.error(f"Error fetching historical weather for {location} on {target_date}: {str(e)}")
            return None

    def _parse_visual_crossing_current_weather(self, location: str, target_date: date, data: Dict) -> WeatherData:
        """Parse current weather data from Visual Crossing API"""
        try:
            # Visual Crossing current weather structure
            current = data.get('currentConditions', {})
            if not current:
                return WeatherData(location=location, date=target_date)

            # Map weather condition
            condition_map = {
                'clear': WeatherCondition.CLEAR,
                'partly cloudy': WeatherCondition.CLOUDY,
                'cloudy': WeatherCondition.CLOUDY,
                'overcast': WeatherCondition.CLOUDY,
                'rain': WeatherCondition.RAIN,
                'snow': WeatherCondition.SNOW,
                'thunderstorm': WeatherCondition.STORM,
                'fog': WeatherCondition.FOG,
                'mist': WeatherCondition.FOG
            }

            conditions = current.get('conditions', '').lower()
            weather_condition = WeatherCondition.CLEAR
            for key, value in condition_map.items():
                if key in conditions:
                    weather_condition = value
                    break

            # Calculate seasonal index
            day_of_year = target_date.timetuple().tm_yday
            if np is not None:
                seasonal_index = round(np.sin(2 * np.pi * day_of_year / 365), 2)
            else:
                seasonal_index = round(math.sin(2 * math.pi * day_of_year / 365), 2)

            return WeatherData(
                location=location,
                date=target_date,
                temperature_avg=current.get('temp'),
                temperature_min=current.get('temp'),
                temperature_max=current.get('temp'),
                precipitation=current.get('precip', 0),
                humidity=current.get('humidity'),
                wind_speed=current.get('windspeed'),
                weather_condition=weather_condition,
                seasonal_index=seasonal_index
            )

        except Exception as e:
            logger.error(f"Error parsing Visual Crossing current weather: {str(e)}")
            return WeatherData(location=location, date=target_date)

    def _parse_visual_crossing_forecast(self, location: str, days_data: List[Dict]) -> List[WeatherData]:
        """Parse forecast data from Visual Crossing API"""
        try:
            forecast_data = []

            for day_data in days_data:
                try:
                    # Parse date
                    date_str = day_data.get('datetime', '')
                    forecast_date = datetime.fromisoformat(date_str).date()

                    # Map weather condition
                    condition_map = {
                        'clear': WeatherCondition.CLEAR,
                        'partly cloudy': WeatherCondition.CLOUDY,
                        'cloudy': WeatherCondition.CLOUDY,
                        'overcast': WeatherCondition.CLOUDY,
                        'rain': WeatherCondition.RAIN,
                        'snow': WeatherCondition.SNOW,
                        'thunderstorm': WeatherCondition.STORM,
                        'fog': WeatherCondition.FOG,
                        'mist': WeatherCondition.FOG
                    }

                    conditions = day_data.get('conditions', '').lower()
                    weather_condition = WeatherCondition.CLEAR
                    for key, value in condition_map.items():
                        if key in conditions:
                            weather_condition = value
                            break

                    # Calculate seasonal index
                    day_of_year = forecast_date.timetuple().tm_yday
                    if np is not None:
                        seasonal_index = round(np.sin(2 * np.pi * day_of_year / 365), 2)
                    else:
                        seasonal_index = round(math.sin(2 * math.pi * day_of_year / 365), 2)

                    # Calculate average temperature
                    temp_min = day_data.get('tempmin')
                    temp_max = day_data.get('tempmax')
                    temp_avg = (temp_min + temp_max) / 2 if temp_min and temp_max else day_data.get('temp')

                    weather_point = WeatherData(
                        location=location,
                        date=forecast_date,
                        temperature_avg=temp_avg,
                        temperature_min=temp_min,
                        temperature_max=temp_max,
                        precipitation=day_data.get('precip', 0),
                        humidity=day_data.get('humidity'),
                        wind_speed=day_data.get('windspeed'),
                        weather_condition=weather_condition,
                        seasonal_index=seasonal_index
                    )

                    forecast_data.append(weather_point)

                except Exception as e:
                    logger.error(f"Error parsing forecast day: {str(e)}")
                    continue

            return forecast_data

        except Exception as e:
            logger.error(f"Error parsing Visual Crossing forecast data: {str(e)}")
            return []

    def _parse_visual_crossing_historical(self, location: str, target_date: date, data: Dict) -> Optional[WeatherData]:
        """Parse historical weather data from Visual Crossing API"""
        try:
            days_data = data.get('days', [])
            if not days_data:
                return None

            # Find the specific date
            for day_data in days_data:
                date_str = day_data.get('datetime', '')
                if date_str.startswith(target_date.isoformat()):
                    # Use the same parsing logic as forecast
                    weather_list = self._parse_visual_crossing_forecast(location, [day_data])
                    return weather_list[0] if weather_list else None

            return None

        except Exception as e:
            logger.error(f"Error parsing Visual Crossing historical data: {str(e)}")
            return None

class HolidayDataProvider:
    
    def __init__(self, cache_ttl: int = 86400):
        self.cache = TTLCache(maxsize=500, ttl=cache_ttl)
        self.custom_holidays = {}  # For custom regional holidays
        
    def get_holidays(self, country: str, year: int, region: Optional[str] = None) -> List[HolidayData]:
        """Get holidays for a specific country and year"""
        try:
            cache_key = f"holidays_{country}_{year}_{region or 'national'}"
            if cache_key in self.cache:
                return self.cache[cache_key]
            
            holiday_data = []
            
            # Get holidays using holidays library
            try:
                country_holidays = holidays.country_holidays(country, years=year)
                
                for holiday_date, holiday_name in country_holidays.items():
                    holiday_type = self._classify_holiday(holiday_name, country)
                    impact_days = self._get_holiday_impact_days(holiday_name, holiday_type)
                    
                    holiday_data.append(HolidayData(
                        country=country,
                        region=region,
                        date=holiday_date,
                        name=holiday_name,
                        type=holiday_type,
                        is_observed=True,
                        impact_days=impact_days
                    ))
                    
            except Exception as e:
                logger.warning(f"Could not get holidays for {country}: {str(e)}")
            
            # Add custom regional holidays if available
            if region and f"{country}_{region}" in self.custom_holidays:
                regional_holidays = self.custom_holidays[f"{country}_{region}"].get(year, [])
                holiday_data.extend(regional_holidays)
            
            # Sort by date
            holiday_data.sort(key=lambda x: x.date)
            
            self.cache[cache_key] = holiday_data
            logger.info(f"Retrieved {len(holiday_data)} holidays for {country} {year}")
            
            return holiday_data
            
        except Exception as e:
            logger.error(f"Error retrieving holidays: {str(e)}")
            return []
    
    def is_holiday_period(self, target_date: date, country: str, region: Optional[str] = None) -> bool:
        """Check if a date falls within a holiday period"""
        try:
            year = target_date.year
            holidays_list = self.get_holidays(country, year, region)
            
            for holiday in holidays_list:
                # Check if date is within holiday impact period
                start_date = holiday.date
                end_date = holiday.date + timedelta(days=holiday.impact_days - 1)
                
                if start_date <= target_date <= end_date:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking holiday period: {str(e)}")
            return False
    
    def get_next_holiday(self, target_date: date, country: str, region: Optional[str] = None) -> Optional[HolidayData]:
        """Get the next upcoming holiday"""
        try:
            year = target_date.year
            holidays_list = self.get_holidays(country, year, region)
            
            # Also check next year if we're near the end of current year
            if target_date.month >= 11:
                next_year_holidays = self.get_holidays(country, year + 1, region)
                holidays_list.extend(next_year_holidays)
            
            # Find next holiday
            upcoming_holidays = [h for h in holidays_list if h.date > target_date]
            if upcoming_holidays:
                return min(upcoming_holidays, key=lambda x: x.date)
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding next holiday: {str(e)}")
            return None
    
    def _classify_holiday(self, holiday_name: str, country: str) -> HolidayType:
        """Classify holiday type based on name and country"""
        name_lower = holiday_name.lower()
        
        # Major holidays (high business impact)
        major_keywords = ['christmas', 'new year', 'thanksgiving', 'easter', 'independence']
        if any(keyword in name_lower for keyword in major_keywords):
            return HolidayType.MAJOR
        
        # Religious holidays
        religious_keywords = ['easter', 'christmas', 'ramadan', 'diwali', 'hanukkah']
        if any(keyword in name_lower for keyword in religious_keywords):
            return HolidayType.RELIGIOUS
        
        # National holidays
        national_keywords = ['independence', 'national', 'republic', 'constitution']
        if any(keyword in name_lower for keyword in national_keywords):
            return HolidayType.NATIONAL
        
        # Default to minor
        return HolidayType.MINOR
    
    def _get_holiday_impact_days(self, holiday_name: str, holiday_type: HolidayType) -> int:
        """Get the number of days a holiday typically impacts business"""
        name_lower = holiday_name.lower()
        
        # Extended impact holidays
        if 'christmas' in name_lower or 'new year' in name_lower:
            return 3
        elif 'thanksgiving' in name_lower:
            return 4  # Including Black Friday
        elif holiday_type == HolidayType.MAJOR:
            return 2
        else:
            return 1
    
    def add_custom_holiday(self, country: str, region: str, holiday: HolidayData):
        """Add a custom regional holiday"""
        key = f"{country}_{region}"
        if key not in self.custom_holidays:
            self.custom_holidays[key] = {}
        
        year = holiday.date.year
        if year not in self.custom_holidays[key]:
            self.custom_holidays[key][year] = []
        
        self.custom_holidays[key][year].append(holiday)

class EventDataProvider:
    """Provider for event data (placeholder for future implementation)"""
    
    def __init__(self, cache_ttl: int = 3600):
        self.cache = TTLCache(maxsize=200, ttl=cache_ttl)
    
    async def get_events(self, location: str, start_date: date, end_date: date) -> List[EventData]:
        """Get events for a location and date range (placeholder)"""
        # This would integrate with event APIs like Eventbrite, local event calendars, etc.
        # For now, return empty list
        logger.info(f"Event data not yet implemented for {location}")
        return []

class ExternalDataService:
    """Main service for coordinating external data providers"""
    
    def __init__(self, config: ExternalFactorConfig):
        self.config = config
        self.weather_provider = None
        self.holiday_provider = HolidayDataProvider(config.holiday_cache_ttl)
        self.event_provider = EventDataProvider()
        
        # Initialize weather provider if API key is available
        if config.virtualcrossing_api_key and config.weather_enabled:
            self.weather_provider = WeatherDataProvider(
                config.virtualcrossing_api_key, 
                config.weather_cache_ttl
            )
    
    async def get_external_factors(self, request: ExternalFactorRequest) -> ExternalFactorSummary:
        """Get comprehensive external factor data"""
        try:
            weather_data = []
            holiday_data = []
            event_data = []
            
            # Get weather data
            if request.include_weather and self.weather_provider and self.config.weather_enabled:
                weather_data = await self.weather_provider.get_weather_data(
                    request.location, request.start_date, request.end_date
                )
            
            # Get holiday data
            if request.include_holidays and self.config.holidays_enabled:
                country = request.country or "KW"  # Default to KW if None
                for year in range(request.start_date.year, request.end_date.year + 1):
                    year_holidays = self.holiday_provider.get_holidays(
                        country, year, request.region
                    )
                    # Filter holidays within date range
                    filtered_holidays = [
                        h for h in year_holidays 
                        if request.start_date <= h.date <= request.end_date
                    ]
                    holiday_data.extend(filtered_holidays)
            
            # Get event data
            if request.include_events and self.config.events_enabled:
                event_data = await self.event_provider.get_events(
                    request.location, request.start_date, request.end_date
                )
            
            # Calculate data quality score
            data_quality_score = self._calculate_data_quality(weather_data, holiday_data, event_data, request)
            
            # Create summary
            date_range = f"{request.start_date.isoformat()} to {request.end_date.isoformat()}"
            summary = ExternalFactorSummary(
                location=request.location,
                date_range=date_range,
                weather_data=weather_data,
                holiday_data=holiday_data,
                event_data=event_data,
                data_quality_score=data_quality_score
            )
            
            logger.info(f"Retrieved external factors for {request.location}: "
                       f"{len(weather_data)} weather points, {len(holiday_data)} holidays, "
                       f"{len(event_data)} events")
            
            return summary
            
        except Exception as e:
            logger.error(f"Error retrieving external factors: {str(e)}")
            # Return empty summary on error
            return ExternalFactorSummary(
                location=request.location,
                date_range=f"{request.start_date.isoformat()} to {request.end_date.isoformat()}",
                data_quality_score=0.0
            )
    
    def _calculate_data_quality(self, weather_data: List[WeatherData], 
                               holiday_data: List[HolidayData], 
                               event_data: List[EventData],
                               request: ExternalFactorRequest) -> float:
        """Calculate overall data quality score"""
        try:
            total_days = (request.end_date - request.start_date).days + 1
            quality_scores = []
            
            # Weather data quality
            if request.include_weather:
                weather_completeness = len(weather_data) / total_days if total_days > 0 else 0
                quality_scores.append(min(weather_completeness, 1.0))
            
            # Holiday data quality (always high if holidays library works)
            if request.include_holidays:
                quality_scores.append(1.0 if holiday_data or total_days < 365 else 0.8)
            
            # Event data quality (placeholder)
            if request.include_events:
                quality_scores.append(0.5)  # Placeholder score
            
            # Return average quality score
            return sum(quality_scores) / len(quality_scores) if quality_scores else 1.0
            
        except Exception as e:
            logger.error(f"Error calculating data quality: {str(e)}")
            return 0.5

    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        stats = {}
        
        if self.weather_provider:
            stats['weather'] = {
                'daily_calls': self.weather_provider.usage_stats.daily_calls,
                'monthly_calls': self.weather_provider.usage_stats.monthly_calls,
                'daily_cost': self.weather_provider.usage_stats.daily_cost,
                'monthly_cost': self.weather_provider.usage_stats.monthly_cost
            }
        
        return stats
