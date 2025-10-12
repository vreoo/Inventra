import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import logging
from statsforecast import StatsForecast
from statsforecast.models import (
    AutoARIMA,
    AutoETS,
    SeasonalNaive,
    Naive,
    RandomWalkWithDrift,
    SklearnModel,
    CrostonClassic,
    CrostonOptimized,
    CrostonSBA,
)
try:
    from statsforecast.models import TBATS as StatsForecastTBATS

    HAS_TBATS = True
except Exception:  # pragma: no cover - optional dependency
    HAS_TBATS = False
from sklearn.linear_model import LinearRegression
from models.forecast import (
    InventoryData, ForecastConfig, ForecastResult, ForecastPoint, 
    ForecastInsight, ForecastModel
)

logger = logging.getLogger(__name__)

class ForecastEngine:
    def __init__(self):
        self.model_mapping = {
            ForecastModel.AUTO_ARIMA: AutoARIMA,
            ForecastModel.AUTO_ETS: AutoETS,
            ForecastModel.SEASONAL_NAIVE: SeasonalNaive,
            ForecastModel.NAIVE: Naive,
            ForecastModel.RANDOM_WALK_DRIFT: RandomWalkWithDrift,
            ForecastModel.SKLEARN_MODEL: SklearnModel,
            ForecastModel.CROSTON_CLASSIC: CrostonClassic,
            ForecastModel.CROSTON_OPTIMIZED: CrostonOptimized,
            ForecastModel.CROSTON_SBA: CrostonSBA,
        }
        if HAS_TBATS:
            self.model_mapping[ForecastModel.TBATS] = StatsForecastTBATS
        else:
            self.model_mapping[ForecastModel.TBATS] = AutoETS
    
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
        
        # Prepare model
        model_class = self.model_mapping.get(config.model, AutoARIMA)

        # Special handling for SklearnModel which requires a sklearn estimator and exogenous variables
        if config.model == ForecastModel.SKLEARN_MODEL:
            # Using LinearRegression as a default sklearn model
            # In a production environment, you might want to make this configurable
            sklearn_model = LinearRegression()
            # For now, we'll not use prediction intervals to avoid the data size issue
            model = model_class(model=sklearn_model)
        elif config.model == ForecastModel.TBATS and HAS_TBATS:
            seasonal_periods = []
            if config.frequency == "D":
                seasonal_periods = [7, 30]
            elif config.frequency == "W":
                seasonal_periods = [52]
            elif config.frequency == "M":
                seasonal_periods = [12]
            if config.seasonal_length:
                seasonal_periods.append(config.seasonal_length)
            seasonal_periods = seasonal_periods or [7]
            model = model_class(seasonal_periods=seasonal_periods)
        else:
            # Configure model parameters based on config
            model_params = {}
            if config.seasonal_length and config.model in [
                ForecastModel.SEASONAL_NAIVE,
                ForecastModel.AUTO_ETS,
            ]:
                model_params['season_length'] = config.seasonal_length
            
            model = model_class(**model_params)

        if hasattr(model, "alias"):
            model.alias = config.model.value
        
        # Create StatsForecast instance
        sf = StatsForecast(
            models=[model],
            freq=config.frequency,
            n_jobs=1
        )
        
        # Generate forecast
        # Special handling for SklearnModel which requires exogenous variables
        if config.model == ForecastModel.SKLEARN_MODEL:
            # Create exogenous variables for training data
            # For now, we'll use simple time-based features
            df['trend'] = range(len(df))
            df['sin_t'] = np.sin(2 * np.pi * df['trend'] / 7)  # Weekly seasonality
            df['cos_t'] = np.cos(2 * np.pi * df['trend'] / 7)  # Weekly seasonality
            
            # Create future exogenous variables for forecasting
            future_dates = pd.date_range(start=df['ds'].max() + pd.Timedelta(days=1), periods=config.horizon, freq=config.frequency)
            future_df = pd.DataFrame({'ds': future_dates, 'unique_id': product_id})
            future_df['trend'] = range(len(df), len(df) + config.horizon)
            future_df['sin_t'] = np.sin(2 * np.pi * future_df['trend'] / 7)  # Weekly seasonality
            future_df['cos_t'] = np.cos(2 * np.pi * future_df['trend'] / 7)  # Weekly seasonality
            
            # Generate forecast with exogenous variables (without level for SklearnModel)
            forecast_df = sf.forecast(df=df, h=config.horizon, X_df=future_df)
        else:
            forecast_df = sf.forecast(df=df, h=config.horizon, level=[int(config.confidence_level * 100)])
        
        forecast_df = self._flatten_forecast_columns(forecast_df)
        
        # Convert forecast to ForecastPoint objects
        forecast_points = []
        last_date = pd.to_datetime(product_data[-1].date)
        
        # Determine the model column name
        if config.model == ForecastModel.SKLEARN_MODEL:
            # For SklearnModel, the column name is the sklearn model class name
            model_column_name = "LinearRegression"
        else:
            model_column_name = config.model.value
        
        for i, row in forecast_df.iterrows():
            forecast_date = last_date + timedelta(days=i+1)
            
            # Get confidence intervals if available
            lower_col = f"{model_column_name}-lo-{int(config.confidence_level * 100)}"
            upper_col = f"{model_column_name}-hi-{int(config.confidence_level * 100)}"
            
            point = ForecastPoint(
                date=forecast_date.strftime("%Y-%m-%d"),
                forecast=float(row[model_column_name]),
                lower_bound=float(row[lower_col]) if lower_col in row else None,
                upper_bound=float(row[upper_col]) if upper_col in row else None
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
            
            # Prepare model
            model_class = self.model_mapping[config.model]
            # Special handling for SklearnModel which requires a sklearn estimator
            if config.model == ForecastModel.SKLEARN_MODEL:
                # Using LinearRegression as a default sklearn model
                sklearn_model = LinearRegression()
                model = model_class(model=sklearn_model)
            else:
                model = model_class()

            if hasattr(model, "alias"):
                model.alias = config.model.value
            
            sf = StatsForecast(
                models=[model],
                freq=config.frequency,
                n_jobs=1
            )
            
            # Generate forecast for test period
            # Special handling for SklearnModel which requires exogenous variables
            if config.model == ForecastModel.SKLEARN_MODEL:
                # Create exogenous variables for training data
                train_df['trend'] = range(len(train_df))
                train_df['sin_t'] = np.sin(2 * np.pi * train_df['trend'] / 7)  # Weekly seasonality
                train_df['cos_t'] = np.cos(2 * np.pi * train_df['trend'] / 7)  # Weekly seasonality
                
                # Create future exogenous variables for forecasting
                future_dates = pd.date_range(start=train_df['ds'].max() + pd.Timedelta(days=1), periods=len(test_df), freq=config.frequency)
                future_df = pd.DataFrame({'ds': future_dates, 'unique_id': train_df['unique_id'].iloc[0]})
                future_df['trend'] = range(len(train_df), len(train_df) + len(test_df))
                future_df['sin_t'] = np.sin(2 * np.pi * future_df['trend'] / 7)  # Weekly seasonality
                future_df['cos_t'] = np.cos(2 * np.pi * future_df['trend'] / 7)  # Weekly seasonality
                
                forecast_df = sf.forecast(df=train_df, h=len(test_df), X_df=future_df)
            else:
                forecast_df = sf.forecast(df=train_df, h=len(test_df))
            
            forecast_df = self._flatten_forecast_columns(forecast_df)
            
            # Calculate metrics
            actual = test_df['y'].values
            # Determine the model column name
            if config.model == ForecastModel.SKLEARN_MODEL:
                model_column_name = "LinearRegression"
            else:
                model_column_name = config.model.value
            predicted = forecast_df[model_column_name].values
            
            mae = np.mean(np.abs(actual - predicted))
            mse = np.mean((actual - predicted) ** 2)
            rmse = np.sqrt(mse)
            
            # Handle MAPE calculation with division by zero protection
            # Only calculate MAPE for non-zero actual values
            non_zero_mask = actual != 0
            if np.any(non_zero_mask):
                mape_values = np.abs((actual[non_zero_mask] - predicted[non_zero_mask]) / actual[non_zero_mask])
                mape = np.mean(mape_values) * 100
            else:
                # If all actual values are zero, MAPE is undefined, use a large value or None
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

    def _flatten_forecast_columns(self, forecast_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize StatsForecast output to use flat column names."""
        if isinstance(forecast_df.columns, pd.MultiIndex):
            flattened = []
            for col in forecast_df.columns:
                if not isinstance(col, tuple):
                    flattened.append(col)
                    continue
                parts = [str(level) for level in col if level not in (None, "",)]
                if parts and parts[0] == "mean":
                    # Revert StatsForecast mean column naming when model name is missing
                    parts = ["mean"]
                if len(parts) > 1 and parts[1].lower() == "mean":
                    parts = [parts[0]]
                flattened.append("-".join(parts))
            forecast_df = forecast_df.copy()
            forecast_df.columns = flattened
        return forecast_df
