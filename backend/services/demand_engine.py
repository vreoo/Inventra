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
            if len(sku_df) < 3:
                logger.warning("Skipping SKU %s due to insufficient history", sku)
                continue

            outcome = self._forecast_single_sku(
                sku,
                sku_df,
                artifacts,
                config,
            )

            forecast_points = self._to_forecast_points(
                forecast_df=outcome.forecast_df,
                model_column=outcome.model_column,
                confidence_level=config.confidence_level,
            )
            starting_inventory = artifacts.inventory_on_hand.get(sku, 0.0)

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
                accuracy_metrics=None,
                safety_stock=float(round(outcome.safety_stock, 2)),
                recommended_order_qty=outcome.recommended_order_qty,
                service_level=outcome.service_level,
                lead_time_days=outcome.lead_time_days,
                starting_inventory=float(round(starting_inventory, 2)),
                demand_frequency=artifacts.frequency,
                schema_version=schema_version,
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
        artifacts: DemandArtifacts,
        config: ForecastConfig,
    ) -> PlanningOutcome:
        model = self._select_model(sku_df, artifacts, config)
        freq = artifacts.frequency
        level = [int(config.confidence_level * 100)]
        sf = StatsForecast(models=[model], freq=freq, n_jobs=1)

        forecast_df = sf.forecast(df=sku_df, h=config.horizon, level=level)
        model_name = model.__class__.__name__

        lead_time_days = artifacts.lead_times.get(
            sku, int(config.lead_time_days_default)
        )

        demand_stats = self._calculate_demand_stats(
            sku_df, freq, lead_time_days, config.service_level
        )

        safety_stock, reorder_point = self._calculate_policies(
            demand_stats, lead_time_days
        )

        reorder_date, stockout_date, recommended_qty = self._simulate_inventory(
            forecast_df,
            model_name,
            artifacts.inventory_on_hand.get(sku, 0.0),
            reorder_point,
            demand_stats,
        )

        insights = self._generate_insights(
            sku_df, forecast_df, reorder_date, stockout_date, recommended_qty
        )

        return PlanningOutcome(
            forecast_df=forecast_df,
            model_used=model_name,
            model_column=model_name,
            safety_stock=safety_stock,
            reorder_point=reorder_point,
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
            return CrostonClassic()

        model_class = _MODEL_MAP.get(desired, AutoARIMA)
        model_kwargs: Dict[str, int] = {}
        if desired in {ForecastModel.AUTO_ETS, ForecastModel.SEASONAL_NAIVE}:
            if artifacts.frequency == "W":
                model_kwargs["season_length"] = 52
            elif artifacts.frequency == "M":
                model_kwargs["season_length"] = 12
            elif config.seasonal_length:
                model_kwargs["season_length"] = config.seasonal_length

        return model_class(**model_kwargs)

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
