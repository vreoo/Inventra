import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from sklearn.metrics import mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

from models.forecast import (
    InventoryData, ForecastConfig, ForecastResult, ForecastPoint, 
    ForecastInsight, ForecastModel
)

logger = logging.getLogger(__name__)

class ForecastEngine:
    def __init__(self):
        self.model_mapping = {
            ForecastModel.AUTO_ARIMA: self._arima_forecast,
            ForecastModel.AUTO_ETS: self._ets_forecast,
            ForecastModel.SEASONAL_NAIVE: self._seasonal_naive_forecast,
            ForecastModel.NAIVE: self._naive_forecast,
            ForecastModel.RANDOM_WALK_DRIFT: self._random_walk_drift_forecast
        }
    
    def generate_forecast(
        self, 
        inventory_data: List[InventoryData], 
        config: ForecastConfig
    ) -> List[ForecastResult]:
        """Generate forecasts for inventory data"""
        try:
            # Group data by product
            products_data = self._group_by_product(inventory_data)
            results = []
            
            for product_id, product_data in products_data.items():
                try:
                    result = self._forecast_single_product(product_id, product_data, config)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error forecasting product {product_id}: {str(e)}")
                    # Create error result
                    error_result = ForecastResult(
                        product_id=product_id,
                        product_name=product_data[0].product_name if product_data else None,
                        model_used=config.model.value,
                        forecast_points=[],
                        insights=[ForecastInsight(
                            type="error",
                            message=f"Failed to generate forecast: {str(e)}",
                            severity="critical"
                        )]
                    )
                    results.append(error_result)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in forecast generation: {str(e)}")
            raise
    
    def _group_by_product(self, inventory_data: List[InventoryData]) -> Dict[str, List[InventoryData]]:
        """Group inventory data by product ID"""
        products = {}
        for item in inventory_data:
            if item.product_id not in products:
                products[item.product_id] = []
            products[item.product_id].append(item)
        
        # Sort each product's data by date
        for product_id in products:
            products[product_id].sort(key=lambda x: x.date)
        
        return products
    
    def _forecast_single_product(
        self, 
        product_id: str, 
        product_data: List[InventoryData], 
        config: ForecastConfig
    ) -> ForecastResult:
        """Generate forecast for a single product"""
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'ds': pd.to_datetime(item.date),
                'y': item.quantity,
                'unique_id': product_id
            }
            for item in product_data
        ])
        
        # Validate data
        if len(df) < 3:
            raise ValueError(f"Insufficient data points for product {product_id}. Need at least 3 points.")
        
        # Sort by date
        df = df.sort_values('ds').reset_index(drop=True)
        
        # Generate forecast using selected model
        forecast_method = self.model_mapping[config.model]
        forecast_values, confidence_intervals = forecast_method(df, config)
        
        # Convert forecast to ForecastPoint objects
        forecast_points = []
        last_date = df['ds'].iloc[-1]
        
        for i in range(config.horizon):
            forecast_date = last_date + timedelta(days=i+1)
            
            point = ForecastPoint(
                date=forecast_date.strftime("%Y-%m-%d"),
                forecast=float(forecast_values[i]),
                lower_bound=float(confidence_intervals[i][0]) if confidence_intervals else None,
                upper_bound=float(confidence_intervals[i][1]) if confidence_intervals else None
            )
            forecast_points.append(point)
        
        # Generate insights and recommendations
        insights = self._generate_insights(product_data, forecast_points, config)
        
        # Calculate key metrics
        stockout_date, reorder_point, reorder_date = self._calculate_inventory_metrics(
            product_data, forecast_points
        )
        
        # Detect peak season
        peak_season = self._detect_peak_season(product_data)
        
        # Calculate accuracy metrics if possible (using last 20% of data for validation)
        accuracy_metrics = self._calculate_accuracy_metrics(df, config) if len(df) > 10 else None
        
        return ForecastResult(
            product_id=product_id,
            product_name=product_data[0].product_name,
            model_used=config.model.value,
            forecast_points=forecast_points,
            stockout_date=stockout_date,
            reorder_point=reorder_point,
            reorder_date=reorder_date,
            peak_season=peak_season,
            insights=insights,
            accuracy_metrics=accuracy_metrics
        )
    
    def _naive_forecast(self, df: pd.DataFrame, config: ForecastConfig) -> Tuple[np.ndarray, Optional[List[Tuple[float, float]]]]:
        """Simple naive forecast - last value repeated"""
        last_value = df['y'].iloc[-1]
        forecast = np.full(config.horizon, last_value)
        
        # Simple confidence intervals based on historical variance
        std = df['y'].std()
        z_score = 1.96  # 95% confidence
        margin = z_score * std
        
        confidence_intervals = [(last_value - margin, last_value + margin) for _ in range(config.horizon)]
        
        return forecast, confidence_intervals
    
    def _seasonal_naive_forecast(self, df: pd.DataFrame, config: ForecastConfig) -> Tuple[np.ndarray, Optional[List[Tuple[float, float]]]]:
        """Seasonal naive forecast"""
        season_length = config.seasonal_length or 7  # Default to weekly seasonality
        
        if len(df) < season_length:
            return self._naive_forecast(df, config)
        
        # Use last season's values
        seasonal_values = df['y'].iloc[-season_length:].values
        forecast = np.tile(seasonal_values, (config.horizon // season_length) + 1)[:config.horizon]
        
        # Confidence intervals based on seasonal variance
        seasonal_std = np.std(seasonal_values)
        z_score = 1.96
        margin = z_score * seasonal_std
        
        confidence_intervals = [(f - margin, f + margin) for f in forecast]
        
        return forecast, confidence_intervals
    
    def _random_walk_drift_forecast(self, df: pd.DataFrame, config: ForecastConfig) -> Tuple[np.ndarray, Optional[List[Tuple[float, float]]]]:
        """Random walk with drift forecast"""
        values = df['y'].values
        
        # Calculate drift (average change)
        if len(values) > 1:
            drift = np.mean(np.diff(values))
        else:
            drift = 0
        
        # Generate forecast
        last_value = values[-1]
        forecast = np.array([last_value + drift * (i + 1) for i in range(config.horizon)])
        
        # Confidence intervals
        std = np.std(np.diff(values)) if len(values) > 1 else np.std(values)
        z_score = 1.96
        
        confidence_intervals = []
        for i in range(config.horizon):
            margin = z_score * std * np.sqrt(i + 1)  # Increasing uncertainty over time
            confidence_intervals.append((forecast[i] - margin, forecast[i] + margin))
        
        return forecast, confidence_intervals
    
    def _arima_forecast(self, df: pd.DataFrame, config: ForecastConfig) -> Tuple[np.ndarray, Optional[List[Tuple[float, float]]]]:
        """ARIMA-like forecast using linear regression with polynomial features"""
        values = df['y'].values
        
        # Create time features
        X = np.arange(len(values)).reshape(-1, 1)
        
        # Use polynomial features to capture trends
        poly_features = PolynomialFeatures(degree=min(2, len(values) - 1))
        X_poly = poly_features.fit_transform(X)
        
        # Fit linear regression
        model = LinearRegression()
        model.fit(X_poly, values)
        
        # Generate forecast
        future_X = np.arange(len(values), len(values) + config.horizon).reshape(-1, 1)
        future_X_poly = poly_features.transform(future_X)
        forecast = model.predict(future_X_poly)
        
        # Ensure non-negative forecasts
        forecast = np.maximum(forecast, 0)
        
        # Calculate confidence intervals based on residuals
        predictions = model.predict(X_poly)
        residuals = values - predictions
        std_residual = np.std(residuals)
        z_score = 1.96
        
        confidence_intervals = []
        for i, f in enumerate(forecast):
            margin = z_score * std_residual * np.sqrt(1 + (i + 1) * 0.1)  # Increasing uncertainty
            confidence_intervals.append((max(0, f - margin), f + margin))
        
        return forecast, confidence_intervals
    
    def _ets_forecast(self, df: pd.DataFrame, config: ForecastConfig) -> Tuple[np.ndarray, Optional[List[Tuple[float, float]]]]:
        """Exponential smoothing forecast"""
        values = df['y'].values
        
        # Simple exponential smoothing
        alpha = 0.3  # Smoothing parameter
        
        # Initialize
        smoothed = [values[0]]
        
        # Apply exponential smoothing
        for i in range(1, len(values)):
            smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[-1])
        
        # Forecast
        last_smoothed = smoothed[-1]
        
        # Add trend if data shows clear trend
        if len(values) > 5:
            recent_trend = np.mean(np.diff(values[-5:]))
            trend_factor = 0.1  # Damping factor for trend
        else:
            recent_trend = 0
            trend_factor = 0
        
        # Generate forecast with trend
        forecast = np.array([last_smoothed + recent_trend * trend_factor * (i + 1) for i in range(config.horizon)])
        forecast = np.maximum(forecast, 0)  # Ensure non-negative
        
        # Confidence intervals based on smoothing residuals
        residuals = np.array([values[i] - smoothed[i] for i in range(len(values))])
        std_residual = np.std(residuals)
        z_score = 1.96
        
        confidence_intervals = []
        for i, f in enumerate(forecast):
            margin = z_score * std_residual * np.sqrt(1 + (i + 1) * 0.05)
            confidence_intervals.append((max(0, f - margin), f + margin))
        
        return forecast, confidence_intervals
    
    def _generate_insights(
        self, 
        historical_data: List[InventoryData], 
        forecast_points: List[ForecastPoint],
        config: ForecastConfig
    ) -> List[ForecastInsight]:
        """Generate actionable insights from forecast data"""
        insights = []
        
        # Calculate trends
        recent_quantities = [item.quantity for item in historical_data[-7:]]  # Last 7 days
        forecast_quantities = [point.forecast for point in forecast_points[:7]]  # Next 7 days
        
        recent_avg = np.mean(recent_quantities)
        forecast_avg = np.mean(forecast_quantities)
        
        # Trend analysis
        if forecast_avg > recent_avg * 1.1:
            insights.append(ForecastInsight(
                type="trend",
                message="Inventory levels are expected to increase significantly",
                severity="info",
                value=((forecast_avg - recent_avg) / recent_avg) * 100
            ))
        elif forecast_avg < recent_avg * 0.9:
            insights.append(ForecastInsight(
                type="trend",
                message="Inventory levels are expected to decrease significantly",
                severity="warning",
                value=((recent_avg - forecast_avg) / recent_avg) * 100
            ))
        
        # Stockout risk analysis
        min_forecast = min(point.forecast for point in forecast_points)
        if min_forecast <= 0:
            days_to_stockout = next(
                (i + 1 for i, point in enumerate(forecast_points) if point.forecast <= 0),
                None
            )
            if days_to_stockout:
                severity = "critical" if days_to_stockout <= 7 else "warning"
                insights.append(ForecastInsight(
                    type="stockout_risk",
                    message=f"Potential stockout predicted in {days_to_stockout} days",
                    severity=severity,
                    value=days_to_stockout
                ))
        
        # Volatility analysis
        historical_std = np.std([item.quantity for item in historical_data])
        forecast_std = np.std([point.forecast for point in forecast_points])
        
        if forecast_std > historical_std * 1.5:
            insights.append(ForecastInsight(
                type="volatility",
                message="High volatility expected in forecast period",
                severity="warning",
                value=forecast_std
            ))
        
        # Seasonal patterns
        if len(historical_data) >= 30:  # Need at least 30 days for seasonal analysis
            monthly_avg = {}
            for item in historical_data:
                month = pd.to_datetime(item.date).month
                if month not in monthly_avg:
                    monthly_avg[month] = []
                monthly_avg[month].append(item.quantity)
            
            # Calculate monthly averages
            monthly_means = {month: np.mean(quantities) for month, quantities in monthly_avg.items()}
            
            if len(monthly_means) >= 3:  # Need at least 3 months
                max_month = max(monthly_means, key=monthly_means.get)
                min_month = min(monthly_means, key=monthly_means.get)
                
                if monthly_means[max_month] > monthly_means[min_month] * 1.3:
                    month_names = {
                        1: "January", 2: "February", 3: "March", 4: "April",
                        5: "May", 6: "June", 7: "July", 8: "August",
                        9: "September", 10: "October", 11: "November", 12: "December"
                    }
                    insights.append(ForecastInsight(
                        type="seasonality",
                        message=f"Peak demand typically occurs in {month_names[max_month]}",
                        severity="info",
                        value=monthly_means[max_month]
                    ))
        
        return insights
    
    def _calculate_inventory_metrics(
        self, 
        historical_data: List[InventoryData], 
        forecast_points: List[ForecastPoint]
    ) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """Calculate stockout date, reorder point, and reorder date"""
        
        stockout_date = None
        reorder_point = None
        reorder_date = None
        
        # Find stockout date
        for point in forecast_points:
            if point.forecast <= 0:
                stockout_date = point.date
                break
        
        # Calculate reorder point (safety stock + lead time demand)
        # Using simple heuristic: 1.5 * average daily consumption
        if len(historical_data) >= 7:
            daily_consumption = np.mean([item.quantity for item in historical_data[-7:]])
            reorder_point = max(daily_consumption * 1.5, 5)  # Minimum 5 units
            
            # Find reorder date (when forecast drops below reorder point)
            for point in forecast_points:
                if point.forecast <= reorder_point:
                    reorder_date = point.date
                    break
        
        return stockout_date, reorder_point, reorder_date
    
    def _detect_peak_season(self, historical_data: List[InventoryData]) -> Optional[str]:
        """Detect peak season from historical data"""
        if len(historical_data) < 90:  # Need at least 3 months
            return None
        
        quarterly_avg = {1: [], 2: [], 3: [], 4: []}
        
        for item in historical_data:
            date = pd.to_datetime(item.date)
            quarter = (date.month - 1) // 3 + 1
            quarterly_avg[quarter].append(item.quantity)
        
        # Calculate average for each quarter
        quarter_means = {}
        for quarter, quantities in quarterly_avg.items():
            if quantities:
                quarter_means[quarter] = np.mean(quantities)
        
        if len(quarter_means) >= 2:
            peak_quarter = max(quarter_means, key=quarter_means.get)
            quarter_names = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
            return quarter_names[peak_quarter]
        
        return None
    
    def _calculate_accuracy_metrics(self, df: pd.DataFrame, config: ForecastConfig) -> Dict[str, float]:
        """Calculate forecast accuracy metrics using cross-validation"""
        try:
            # Use last 20% of data for validation
            split_point = int(len(df) * 0.8)
            train_df = df.iloc[:split_point].copy()
            test_df = df.iloc[split_point:].copy()
            
            if len(test_df) < 3:
                return None
            
            # Generate forecast for test period using the same method
            forecast_method = self.model_mapping[config.model]
            test_config = ForecastConfig(
                model=config.model,
                horizon=len(test_df),
                frequency=config.frequency,
                confidence_level=config.confidence_level,
                seasonal_length=config.seasonal_length
            )
            
            predicted_values, _ = forecast_method(train_df, test_config)
            actual_values = test_df['y'].values
            
            # Calculate metrics
            mae = mean_absolute_error(actual_values, predicted_values)
            mse = mean_squared_error(actual_values, predicted_values)
            rmse = np.sqrt(mse)
            
            # Handle MAPE calculation with division by zero protection
            non_zero_mask = actual_values != 0
            if np.any(non_zero_mask):
                mape_values = np.abs((actual_values[non_zero_mask] - predicted_values[non_zero_mask]) / actual_values[non_zero_mask])
                mape = np.mean(mape_values) * 100
            else:
                mape = None
            
            # Ensure all values are finite and JSON serializable
            metrics = {
                "MAE": float(mae) if np.isfinite(mae) else None,
                "MSE": float(mse) if np.isfinite(mse) else None,
                "RMSE": float(rmse) if np.isfinite(rmse) else None,
                "MAPE": float(mape) if mape is not None and np.isfinite(mape) else None
            }
            
            return metrics
            
        except Exception as e:
            logger.warning(f"Could not calculate accuracy metrics: {str(e)}")
            return None
