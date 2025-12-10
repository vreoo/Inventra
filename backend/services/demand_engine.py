import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from statistics import NormalDist
from statsforecast import StatsForecast
from statsforecast.models import (
    AutoARIMA,
    AutoETS,
    CrostonClassic,
    CrostonOptimized,
    CrostonSBA,
    Naive,
    SeasonalNaive,
)
from statsforecast.utils import ConformalIntervals

from models.forecast import (
    ForecastConfig,
    ForecastInsight,
    ForecastMode,
    ForecastModel,
    ForecastPoint,
    ForecastResult,
)
from services.file_handler import DemandArtifacts

logger = logging.getLogger(__name__)

try:
    from statsforecast.models import TBATS as StatsForecastTBATS

    HAS_TBATS = True
except Exception:  # pragma: no cover - optional dependency
    HAS_TBATS = False


_MODEL_MAP = {
    ForecastModel.AUTO_ARIMA: AutoARIMA,
    ForecastModel.AUTO_ETS: AutoETS,
    ForecastModel.SEASONAL_NAIVE: SeasonalNaive,
    ForecastModel.NAIVE: Naive,
    ForecastModel.CROSTON_CLASSIC: CrostonClassic,
    ForecastModel.CROSTON_OPTIMIZED: CrostonOptimized,
    ForecastModel.CROSTON_SBA: CrostonSBA,
    ForecastModel.RANDOM_WALK_DRIFT: Naive,
    ForecastModel.SKLEARN_MODEL: AutoARIMA,  # placeholder fallback
}

INTERMITTENT_THRESHOLD = 0.4


@dataclass
class PlanningOutcome:
    forecast_df: pd.DataFrame
    model_used: str
    model_column: str
    safety_stock: float
    reorder_point: float
    starting_inventory: float
    inventory_estimated: bool
    reorder_date: Optional[str]
    stockout_date: Optional[str]
    recommended_order_qty: Optional[float]
    lead_time_days: int
    service_level: float
    insights: List[ForecastInsight]


class DemandPlanningEngine:
    """Generate demand forecasts and reorder recommendations per SKU."""

    def __init__(self):
        self.freq_to_days = {"D": 1, "W": 7, "M": 30}
        self.exog_compatible_models = {"AutoARIMA"}

    def generate(
        self,
        artifacts: DemandArtifacts,
        config: ForecastConfig,
        schema_version: Optional[str],
    ) -> List[ForecastResult]:
        demand_df = artifacts.demand_df.copy()
        results: List[ForecastResult] = []

        for sku in demand_df["unique_id"].unique():
            sku_df = demand_df[demand_df["unique_id"] == sku].copy()
            exog_df = (
                artifacts.exog_df[artifacts.exog_df["unique_id"] == sku].copy()
                if artifacts.exog_df is not None
                else None
            )

            if len(sku_df) < 3:
                logger.warning("Skipping SKU %s due to insufficient history", sku)
                continue

            outcome = self._forecast_single_sku(
                sku,
                sku_df,
                exog_df,
                artifacts,
                config,
            )

            forecast_points = self._to_forecast_points(
                forecast_df=outcome.forecast_df,
                model_column=outcome.model_column,
                confidence_level=config.confidence_level,
            )

            accuracy_metrics = self._calculate_accuracy_metrics(
                sku_df=sku_df,
                exog_df=exog_df,
                artifacts=artifacts,
                config=config,
            )

            result = ForecastResult(
                product_id=str(sku),
                product_name=str(sku),
                model_used=outcome.model_used,
                forecast_points=forecast_points,
                mode=ForecastMode.DEMAND,
                stockout_date=outcome.stockout_date,
                reorder_point=float(round(outcome.reorder_point, 2)),
                reorder_date=outcome.reorder_date,
                insights=outcome.insights,
                safety_stock=float(round(outcome.safety_stock, 2)),
                recommended_order_qty=outcome.recommended_order_qty,
                service_level=outcome.service_level,
                lead_time_days=outcome.lead_time_days,
                starting_inventory=float(round(outcome.starting_inventory, 2)),
                demand_frequency=artifacts.frequency,
                schema_version=schema_version,
                accuracy_metrics=accuracy_metrics,
            )
            results.append(result)

        return results

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _forecast_single_sku(
        self,
        sku: str,
        sku_df: pd.DataFrame,
        exog_df: Optional[pd.DataFrame],
        artifacts: DemandArtifacts,
        config: ForecastConfig,
    ) -> PlanningOutcome:
        prepared_df, prepared_exog = self._prepare_regular_series(
            sku_df, exog_df, artifacts.frequency
        )

        model = self._select_model(prepared_df, artifacts, config)
        freq = artifacts.frequency
        level = [int(config.confidence_level * 100)]
        if getattr(model, "only_conformal_intervals", False) and getattr(
            model, "prediction_intervals", None
        ) is None:
            logger.info(
                "Skipping prediction intervals for SKU %s (insufficient history for conformal intervals)",
                sku,
            )
            level = None
        sf = StatsForecast(models=[model], freq=freq, n_jobs=1)

        train_df = prepared_df
        future_exog = None
        exog_cols = (
            [col for col in prepared_exog.columns if col not in {"unique_id", "ds"}]
            if prepared_exog is not None
            else []
        )
        if self._model_supports_exog(model) and prepared_exog is not None and exog_cols:
            train_df = prepared_df.merge(prepared_exog, on=["unique_id", "ds"], how="left")
            train_df[exog_cols] = (
                train_df[exog_cols].ffill().bfill().fillna(0)
            )
            future_exog = self._build_future_exog(
                sku=sku,
                last_date=train_df["ds"].max(),
                horizon=config.horizon,
                freq=freq,
                exog_cols=exog_cols,
                prepared_exog=prepared_exog,
            )

        forecast_df = sf.forecast(
            df=train_df,
            h=config.horizon,
            level=level,
            X_df=future_exog,
        )
        forecast_df = self._flatten_forecast_columns(forecast_df)
        model_name = getattr(model, "alias", None) or model.__class__.__name__

        lead_time_days = artifacts.lead_times.get(
            sku, int(config.lead_time_days_default)
        )

        demand_stats = self._calculate_demand_stats(
            prepared_df, freq, lead_time_days, config.service_level
        )

        safety_stock, reorder_point = self._calculate_policies(
            demand_stats, lead_time_days
        )

        starting_inventory, inventory_estimated = self._resolve_starting_inventory(
            sku=sku,
            artifacts=artifacts,
            sku_df=sku_df,
            demand_stats=demand_stats,
            reorder_point=reorder_point,
            lead_time_days=lead_time_days,
        )

        reorder_date, stockout_date, recommended_qty = self._simulate_inventory(
            forecast_df,
            model_name,
            starting_inventory,
            reorder_point,
            demand_stats,
        )

        insights = self._generate_insights(
            sku_df, forecast_df, reorder_date, stockout_date, recommended_qty
        )

        if inventory_estimated:
            insights.insert(
                0,
                ForecastInsight(
                    type="inventory_assumption",
                    message=(
                        f"No on-hand inventory found for {sku}; "
                        f"estimated starting inventory at {starting_inventory:.1f} units "
                        "using recent demand. Include an inventory column for precise "
                        "stockout and reorder dates."
                    ),
                    severity="warning",
                    value=float(round(starting_inventory, 2)),
                ),
            )

        return PlanningOutcome(
            forecast_df=forecast_df,
            model_used=model_name,
            model_column=model_name,
            safety_stock=safety_stock,
            reorder_point=reorder_point,
            starting_inventory=starting_inventory,
            inventory_estimated=inventory_estimated,
            reorder_date=reorder_date,
            stockout_date=stockout_date,
            recommended_order_qty=recommended_qty,
            lead_time_days=lead_time_days,
            service_level=config.service_level,
            insights=insights,
        )

    def _select_model(
        self,
        sku_df: pd.DataFrame,
        artifacts: DemandArtifacts,
        config: ForecastConfig,
    ):
        desired = config.model
        if desired == ForecastModel.TBATS:
            if config.enable_tbats and HAS_TBATS:
                seasonal_periods = self._detect_tbats_seasons(artifacts.frequency)
                logger.info("Using TBATS for SKU %s", sku_df["unique_id"].iloc[0])
                return StatsForecastTBATS(seasonal_periods=seasonal_periods)
            logger.warning("TBATS requested but unavailable. Falling back to AutoETS.")
            desired = ForecastModel.AUTO_ETS

        if self._is_intermittent(sku_df) and desired not in {
            ForecastModel.CROSTON_CLASSIC,
            ForecastModel.CROSTON_OPTIMIZED,
            ForecastModel.CROSTON_SBA,
        }:
            logger.info(
                "Detected intermittent demand for SKU %s -> CrostonClassic",
                sku_df["unique_id"].iloc[0],
            )
            pi = self._build_conformal_intervals(len(sku_df), config.horizon)
            model = CrostonClassic(prediction_intervals=pi)
            if hasattr(model, "alias"):
                model.alias = model.__class__.__name__
            return model

        model_class = _MODEL_MAP.get(desired, AutoARIMA)
        model_kwargs: Dict[str, int] = {}
        if desired in {ForecastModel.AUTO_ETS, ForecastModel.SEASONAL_NAIVE}:
            if artifacts.frequency == "W":
                model_kwargs["season_length"] = 52
            elif artifacts.frequency == "M":
                model_kwargs["season_length"] = 12
            elif config.seasonal_length:
                model_kwargs["season_length"] = config.seasonal_length
        if model_class in {CrostonClassic, CrostonOptimized, CrostonSBA}:
            model_kwargs["prediction_intervals"] = self._build_conformal_intervals(
                len(sku_df), config.horizon
            )

        model_instance = model_class(**model_kwargs)
        if hasattr(model_instance, "alias"):
            model_instance.alias = model_instance.__class__.__name__

        return model_instance

    def _model_supports_exog(self, model) -> bool:
        return model.__class__.__name__ in self.exog_compatible_models

    def _is_intermittent(self, sku_df: pd.DataFrame) -> bool:
        zeros_ratio = (sku_df["y"] == 0).mean()
        return zeros_ratio >= INTERMITTENT_THRESHOLD

    def _detect_tbats_seasons(self, freq: str) -> List[int]:
        if freq == "D":
            return [7, 30]
        if freq == "W":
            return [52]
        if freq == "M":
            return [12]
        return [7]

    def _build_conformal_intervals(
        self, series_length: int, horizon: Optional[int]
    ) -> Optional[ConformalIntervals]:
        """Return conformal interval settings when there is enough history to compute them."""
        if horizon is None:
            return None
        try:
            horizon_int = int(horizon)
        except (TypeError, ValueError):
            return None
        horizon_int = max(horizon_int, 1)
        max_windows = series_length // horizon_int
        if max_windows < 2:
            return None
        return ConformalIntervals(
            n_windows=min(max_windows, 5),
            h=horizon_int,
        )

    def _calculate_demand_stats(
        self,
        sku_df: pd.DataFrame,
        freq: str,
        lead_time_days: int,
        service_level: float,
    ) -> Dict[str, float]:
        period_days = self.freq_to_days.get(freq, 1)
        period_demand = sku_df["y"].astype(float)
        mean_per_period = period_demand.mean()
        std_per_period = period_demand.std(ddof=0) or 0.0

        periods_in_lead = max(1, math.ceil(lead_time_days / period_days))
        z_value = self._service_level_to_z(service_level)

        return {
            "period_days": period_days,
            "mean_per_period": mean_per_period,
            "std_per_period": std_per_period,
            "periods_in_lead": periods_in_lead,
            "z_value": z_value,
        }

    def _service_level_to_z(self, service_level: float) -> float:
        service_level = min(max(service_level, 0.5), 0.999)
        return NormalDist().inv_cdf(service_level)

    def _calculate_policies(
        self, demand_stats: Dict[str, float], lead_time_days: int
    ) -> Tuple[float, float]:
        mean = demand_stats["mean_per_period"]
        std = demand_stats["std_per_period"]
        periods_in_lead = demand_stats["periods_in_lead"]
        z = demand_stats["z_value"]

        lead_time_demand = mean * periods_in_lead
        safety_stock = z * std * math.sqrt(periods_in_lead)
        reorder_point = lead_time_demand + safety_stock

        return max(0.0, safety_stock), max(0.0, reorder_point)

    def _prepare_regular_series(
        self,
        sku_df: pd.DataFrame,
        exog_df: Optional[pd.DataFrame],
        freq: str,
    ) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
        """Ensure consistent frequency and fill missing dates with zeros/ffill."""
        working = sku_df.copy()
        working["ds"] = pd.to_datetime(working["ds"])
        working = working.sort_values("ds")
        base_id = str(working["unique_id"].dropna().iloc[0]) if not working["unique_id"].dropna().empty else None

        all_dates = pd.date_range(start=working["ds"].min(), end=working["ds"].max(), freq=freq or "D")
        reindexed = (
            working.set_index("ds")
            .reindex(all_dates)
            .reset_index()
            .rename(columns={"index": "ds"})
        )
        reindexed["unique_id"] = reindexed["unique_id"].ffill().bfill()
        if base_id is not None:
            reindexed["unique_id"] = reindexed["unique_id"].fillna(base_id)
        reindexed["y"] = reindexed["y"].fillna(0.0).astype(float)

        aligned_exog: Optional[pd.DataFrame] = None
        if exog_df is not None:
            exog_working = exog_df.copy()
            exog_working["ds"] = pd.to_datetime(exog_working["ds"])
            exog_working = exog_working.sort_values("ds")
            exog_cols = [c for c in exog_working.columns if c not in {"ds", "unique_id"}]
            aligned_exog = (
                exog_working.set_index("ds")
                .reindex(all_dates)
                .reset_index()
                .rename(columns={"index": "ds"})
            )
            aligned_exog["unique_id"] = aligned_exog["unique_id"].ffill().bfill()
            if base_id is not None:
                aligned_exog["unique_id"] = aligned_exog["unique_id"].fillna(base_id)
            aligned_exog[exog_cols] = aligned_exog[exog_cols].ffill().bfill().fillna(0)

        return reindexed[["unique_id", "ds", "y"]], aligned_exog

    def _build_future_exog(
        self,
        sku: str,
        last_date: pd.Timestamp,
        horizon: int,
        freq: str,
        exog_cols: List[str],
        prepared_exog: pd.DataFrame,
    ) -> pd.DataFrame:
        """Create future exogenous frame by forward-filling last observed values."""
        future_dates = pd.date_range(start=last_date, periods=horizon + 1, freq=freq)[1:]
        future = pd.DataFrame({"ds": future_dates, "unique_id": sku})
        last_values = prepared_exog.sort_values("ds").iloc[-1]
        for col in exog_cols:
            future[col] = last_values.get(col, 0.0)
        return future

    def _calculate_accuracy_metrics(
        self,
        sku_df: pd.DataFrame,
        exog_df: Optional[pd.DataFrame],
        artifacts: DemandArtifacts,
        config: ForecastConfig,
    ) -> Optional[Dict[str, float]]:
        """Backtest on last 20% of history to surface MAE/MSE/RMSE/MAPE/WAPE/sMAPE."""
        if len(sku_df) < 8:
            return None

        prepared_df, prepared_exog = self._prepare_regular_series(
            sku_df, exog_df, artifacts.frequency
        )

        working = prepared_df.sort_values("ds")
        split_idx = int(len(working) * 0.8)
        train_df = working.iloc[:split_idx].copy()
        test_df = working.iloc[split_idx:].copy()

        if len(train_df) < 3 or len(test_df) < 3:
            return None

        model = self._select_model(train_df, artifacts, config)
        sf = StatsForecast(models=[model], freq=artifacts.frequency, n_jobs=1)

        train_exog = prepared_exog
        exog_cols: List[str] = []
        future_exog = None
        if self._model_supports_exog(model) and prepared_exog is not None:
            exog_cols = [c for c in prepared_exog.columns if c not in {"unique_id", "ds"}]
            train_df = train_df.merge(prepared_exog, on=["unique_id", "ds"], how="left")
            train_df[exog_cols] = train_df[exog_cols].ffill().bfill().fillna(0)
            future_exog = self._build_future_exog(
                sku=train_df["unique_id"].iloc[0],
                last_date=train_df["ds"].max(),
                horizon=len(test_df),
                freq=artifacts.frequency,
                exog_cols=exog_cols,
                prepared_exog=prepared_exog,
            )

        forecast_df = sf.forecast(df=train_df, h=len(test_df), X_df=future_exog)
        forecast_df = self._flatten_forecast_columns(forecast_df)

        model_col = getattr(model, "alias", None) or model.__class__.__name__
        if model_col not in forecast_df.columns:
            # Fall back to first non-date column to stay resilient
            non_ds_cols = [c for c in forecast_df.columns if c != "ds"]
            model_col = non_ds_cols[0] if non_ds_cols else None
        if not model_col:
            return None

        actual = test_df["y"].to_numpy()
        predicted = forecast_df[model_col].to_numpy()

        mae = np.mean(np.abs(actual - predicted))
        mse = np.mean((actual - predicted) ** 2)
        rmse = math.sqrt(mse)

        denom = np.sum(np.abs(actual))
        wape = float(np.sum(np.abs(actual - predicted)) / denom) * 100 if denom > 0 else None

        smape = float(
            np.mean(
                2
                * np.abs(predicted - actual)
                / np.maximum(np.abs(actual) + np.abs(predicted), 1e-8)
            )
            * 100
        )

        non_zero_mask = actual != 0
        mape = (
            float(
                np.mean(
                    np.abs((actual[non_zero_mask] - predicted[non_zero_mask]) / actual[non_zero_mask])
                )
                * 100
            )
            if np.any(non_zero_mask)
            else None
        )

        def safe(val: float) -> Optional[float]:
            return float(val) if val is not None and np.isfinite(val) else None

        return {
            "MAE": safe(mae),
            "MSE": safe(mse),
            "RMSE": safe(rmse),
            "MAPE": safe(mape),
            "WAPE": safe(wape),
            "sMAPE": safe(smape),
        }

    def _resolve_starting_inventory(
        self,
        sku: str,
        artifacts: DemandArtifacts,
        sku_df: pd.DataFrame,
        demand_stats: Dict[str, float],
        reorder_point: float,
        lead_time_days: int,
    ) -> Tuple[float, bool]:
        """Choose on-hand inventory for simulation; estimate when not supplied."""
        if sku in artifacts.inventory_on_hand:
            return float(artifacts.inventory_on_hand[sku]), False

        if "default_sku" in artifacts.inventory_on_hand:
            return float(artifacts.inventory_on_hand["default_sku"]), False

        period_days = max(demand_stats.get("period_days") or 1, 1)
        mean_per_period = demand_stats.get("mean_per_period") or 0.0
        periods_in_lead = max(int(demand_stats.get("periods_in_lead", 1)), 1)

        recent_window = min(len(sku_df), max(7, periods_in_lead))
        recent_mean = float(sku_df["y"].tail(recent_window).mean()) if recent_window else 0.0
        demand_rate = recent_mean if math.isfinite(recent_mean) and recent_mean > 0 else mean_per_period
        if not math.isfinite(demand_rate) or demand_rate < 0:
            demand_rate = 0.0

        coverage_days = max(lead_time_days + period_days, 7)
        coverage_periods = max(1, math.ceil(coverage_days / period_days))
        estimated = demand_rate * coverage_periods

        buffer_periods = max(1, math.ceil(periods_in_lead * 0.5))
        estimated_target = reorder_point + demand_rate * buffer_periods
        estimated = max(estimated, estimated_target)

        return float(round(max(0.0, estimated), 2)), True

    def _simulate_inventory(
        self,
        forecast_df: pd.DataFrame,
        model_column: str,
        starting_inventory: float,
        reorder_point: float,
        demand_stats: Dict[str, float],
    ) -> Tuple[Optional[str], Optional[str], Optional[float]]:
        inventory_level = starting_inventory
        reorder_date: Optional[str] = None
        stockout_date: Optional[str] = None
        recommended_qty: Optional[float] = None

        lead_time_demand = demand_stats["mean_per_period"] * demand_stats["periods_in_lead"]

        for _, row in forecast_df.iterrows():
            forecast_value = float(row.get(model_column, 0.0))
            inventory_level -= forecast_value

            current_date = (
                row["ds"].strftime("%Y-%m-%d")
                if isinstance(row.get("ds"), pd.Timestamp)
                else None
            )

            if reorder_date is None and inventory_level <= reorder_point:
                reorder_date = current_date
                recommended_qty = max(
                    0.0, round((lead_time_demand + reorder_point) - inventory_level, 2)
                )

            if inventory_level <= 0 and stockout_date is None:
                stockout_date = current_date
                break

        return reorder_date, stockout_date, recommended_qty

    def _generate_insights(
        self,
        historical_df: pd.DataFrame,
        forecast_df: pd.DataFrame,
        reorder_date: Optional[str],
        stockout_date: Optional[str],
        recommended_qty: Optional[float],
    ) -> List[ForecastInsight]:
        insights: List[ForecastInsight] = []

        recent = historical_df.tail(7)["y"].mean() if len(historical_df) >= 7 else historical_df["y"].mean()
        upcoming = forecast_df.head(7).iloc[:, 2].mean() if not forecast_df.empty else 0.0

        if upcoming > recent * 1.1:
            increase_pct = ((upcoming - recent) / recent) * 100 if recent else 0
            insights.append(
                ForecastInsight(
                    type="demand_increase",
                    message="Demand is projected to rise in the next week.",
                    severity="info",
                    value=float(round(increase_pct, 2)),
                )
            )

        if reorder_date:
            insights.append(
                ForecastInsight(
                    type="reorder_point",
                    message=f"Place next order by {reorder_date}.",
                    severity="warning",
                )
            )

        if stockout_date:
            insights.append(
                ForecastInsight(
                    type="stockout_risk",
                    message=f"Projected stockout on {stockout_date}.",
                    severity="critical",
                )
            )

        if recommended_qty:
            insights.append(
                ForecastInsight(
                    type="recommended_order",
                    message="Suggested order quantity derived from forecast and policy.",
                    severity="info",
                    value=recommended_qty,
                )
            )

        return insights

    def _to_forecast_points(
        self,
        forecast_df: pd.DataFrame,
        model_column: str,
        confidence_level: float,
    ) -> List[ForecastPoint]:
        points: List[ForecastPoint] = []
        level = int(confidence_level * 100)
        model_col = model_column if model_column in forecast_df.columns else None

        if model_col is None and len(forecast_df.columns) >= 3:
            model_col = forecast_df.columns[2]
            logger.warning(
                "Model column %s not found in forecast output; defaulting to %s",
                model_column,
                model_col,
            )
        elif model_col is None:
            raise ValueError("Forecast output missing model predictions column")

        lower_col = f"{model_col}-lo-{level}"
        upper_col = f"{model_col}-hi-{level}"

        for _, row in forecast_df.iterrows():
            date_value = row["ds"]
            if isinstance(date_value, pd.Timestamp):
                date_str = date_value.strftime("%Y-%m-%d")
            else:
                date_str = str(date_value)

            point = ForecastPoint(
                date=date_str,
                forecast=float(row[model_col]),
                lower_bound=float(row[lower_col]) if lower_col in row else None,
                upper_bound=float(row[upper_col]) if upper_col in row else None,
            )
            points.append(point)

        return points

    def _flatten_forecast_columns(self, forecast_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize StatsForecast output to flat column names for downstream use."""
        if isinstance(forecast_df.columns, pd.MultiIndex):
            flattened: List[str] = []
            for col in forecast_df.columns:
                if not isinstance(col, tuple):
                    flattened.append(col)
                    continue
                parts = [str(level) for level in col if level not in (None, "",)]
                if parts and parts[0] == "mean":
                    parts = ["mean"]
                if len(parts) > 1 and parts[1].lower() == "mean":
                    parts = [parts[0]]
                flattened.append("-".join(parts))
            forecast_df = forecast_df.copy()
            forecast_df.columns = flattened
        return forecast_df
