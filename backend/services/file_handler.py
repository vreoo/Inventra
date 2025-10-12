import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from models.forecast import (
    ColumnMapping,
    ForecastConfig,
    ForecastMode,
    InventoryData,
    ValidationAnomaly,
    ValidationSummary,
)

logger = logging.getLogger(__name__)


@dataclass
class DemandArtifacts:
    demand_df: pd.DataFrame
    inventory_on_hand: Dict[str, float]
    lead_times: Dict[str, int]
    frequency: str
    validation: ValidationSummary


class FileHandler:
    def __init__(self, upload_dir: str = "storage/uploads"):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        self.raw_dir = Path("storage/raw")
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        self.processed_dir = Path("storage/processed")
        self.processed_dir.mkdir(parents=True, exist_ok=True)

        self.metadata_dir = Path("storage/upload_metadata")
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------
    def validate_csv_file(
        self, file_path: Path, mode: ForecastMode = ForecastMode.DEMAND
    ) -> Dict[str, Any]:
        """Validate CSV file and return validation results with mapping hints."""
        try:
            df = pd.read_csv(file_path)
        except Exception as exc:
            logger.error("Error reading CSV %s: %s", file_path, exc)
            return {
                "valid": False,
                "errors": [f"Error reading CSV file: {exc}"],
                "warnings": [],
                "info": {},
                "mapping": {},
            }

        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "info": {
                "rows": len(df),
                "columns": list(df.columns),
                "date_columns": [],
                "numeric_columns": [],
                "text_columns": [],
            },
        }

        if df.empty:
            validation_result["valid"] = False
            validation_result["errors"].append("CSV file is empty")
            return validation_result

        mapping = self._detect_column_mapping(df)

        # Analyse column types
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                validation_result["info"]["numeric_columns"].append(col)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                validation_result["info"]["date_columns"].append(col)
            else:
                try:
                    pd.to_datetime(df[col].head())
                    validation_result["info"]["date_columns"].append(col)
                except Exception:
                    validation_result["info"]["text_columns"].append(col)

        # Basic requirements depending on mode
        required_cols = ["date", "demand"] if mode == ForecastMode.DEMAND else ["date", "demand"]
        missing_required = [field for field in required_cols if not getattr(mapping, field)]

        if missing_required:
            validation_result["valid"] = False
            validation_result["errors"].append(
                f"Missing required column(s) for {mode.value} mode: {', '.join(missing_required)}"
            )

        if not mapping.sku:
            validation_result["warnings"].append(
                "Could not detect SKU/product column. Defaulting to single-product behaviour."
            )

        summary = self._build_validation_summary(df, mapping)
        validation_result["info"].update(summary.dict())
        validation_result["mapping"] = mapping.dict()
        validation_result["summary"] = summary.dict()

        if summary.date_coverage_pct is not None and summary.date_coverage_pct < 0.7:
            validation_result["warnings"].append(
                "Date coverage is below 70%. Consider filling gaps for better accuracy."
            )

        if summary.missing_by_field.get("demand", 0) > 0.05:
            validation_result["warnings"].append(
                "More than 5% of demand values are missing. Fill or clean the dataset."
            )

        if summary.anomalies:
            validation_result["warnings"].append(
                f"Detected {len(summary.anomalies)} potential demand anomalies (|z| >= 3.0)."
            )

        return validation_result

    def process_inventory_data(
        self, file_path: Path, mapping: Optional[ColumnMapping] = None
    ) -> Tuple[List[InventoryData], Dict[str, Any]]:
        """Legacy inventory processing, maintained for backward compatibility."""
        df = pd.read_csv(file_path)
        if mapping is None:
            detected = self._detect_column_mapping(df)
            mapping = ColumnMapping(
                date=detected.date,
                sku=detected.sku,
                demand=detected.demand,
                inventory=detected.inventory,
                lead_time=detected.lead_time,
                name=detected.name,
            )

        if not mapping.date or not mapping.demand:
            raise ValueError("Could not detect required date and quantity columns")

        date_col = mapping.date
        quantity_col = mapping.demand
        product_col = mapping.sku
        product_name_col = mapping.name

        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)

        processed: List[InventoryData] = []
        if product_col:
            grouped = df.groupby(product_col)
            for product_id, group in grouped:
                for _, row in group.iterrows():
                    processed.append(
                        InventoryData(
                            date=row[date_col].strftime("%Y-%m-%d"),
                            product_id=str(product_id),
                            quantity=float(row[quantity_col]),
                            product_name=str(
                                row.get(product_name_col, product_id)
                            )
                            if product_name_col
                            else str(product_id),
                        )
                    )
        else:
            product_id = "default_product"
            for _, row in df.iterrows():
                processed.append(
                    InventoryData(
                        date=row[date_col].strftime("%Y-%m-%d"),
                        product_id=product_id,
                        quantity=float(row[quantity_col]),
                        product_name="Default Product",
                    )
                )

        info = {
            "total_records": len(processed),
            "date_range": {
                "start": min(item.date for item in processed),
                "end": max(item.date for item in processed),
            },
            "products": list({item.product_id for item in processed}),
            "column_mapping": mapping.dict(),
        }
        return processed, info

    def prepare_demand_artifacts(
        self,
        file_id: str,
        mapping: ColumnMapping,
        config: ForecastConfig,
    ) -> DemandArtifacts:
        """Prepare demand series, inventory snapshot, and lead times for demand planning."""
        file_path = self.get_file_path(file_id)
        df = pd.read_csv(file_path)

        if not mapping.date or not mapping.demand:
            raise ValueError("Demand mode requires mapped date and demand columns.")

        sku_col = mapping.sku or "default_sku"
        df[mapping.date] = pd.to_datetime(df[mapping.date])
        df = df.dropna(subset=[mapping.date])
        if mapping.demand not in df.columns:
            raise ValueError(f"Demand column '{mapping.demand}' not found in dataset.")

        df = df.sort_values(mapping.date)
        df["__sku__"] = df[sku_col] if mapping.sku else "default_sku"

        demand_series = (
            df.groupby(["__sku__", mapping.date])[mapping.demand]
            .sum()
            .reset_index()
            .rename(
                columns={
                    "__sku__": "unique_id",
                    mapping.date: "ds",
                    mapping.demand: "y",
                }
            )
        )
        demand_series["ds"] = pd.to_datetime(demand_series["ds"])

        frequency = config.frequency or self._detect_frequency(demand_series["ds"])
        if not frequency:
            frequency = self._detect_frequency(demand_series["ds"])
        if not frequency:
            frequency = "D"

        summary = self._build_validation_summary(df, mapping)

        inventory_snapshot = self._extract_inventory_snapshot(df, mapping)
        lead_times = self._extract_lead_times(df, mapping, config.lead_time_days_default)

        # Persist processed datasets for auditing / re-use
        processed_dir = self.processed_dir / file_id
        processed_dir.mkdir(parents=True, exist_ok=True)
        self._write_frame(demand_series, processed_dir / "demand.parquet")

        inventory_df = (
            pd.DataFrame(
                [
                    {"unique_id": sku, "on_hand": qty}
                    for sku, qty in inventory_snapshot.items()
                ]
            )
            if inventory_snapshot
            else pd.DataFrame(columns=["unique_id", "on_hand"])
        )
        self._write_frame(inventory_df, processed_dir / "inventory.parquet")

        lead_time_df = pd.DataFrame(
            [
                {"unique_id": sku, "lead_time_days": int(days)}
                for sku, days in lead_times.items()
            ]
        )
        self._write_frame(lead_time_df, processed_dir / "lead_time.parquet")

        return DemandArtifacts(
            demand_df=demand_series,
            inventory_on_hand=inventory_snapshot,
            lead_times=lead_times,
            frequency=frequency,
            validation=summary,
        )

    def save_upload_metadata(
        self,
        file_id: str,
        filename: str,
        mode: ForecastMode,
        schema_version: str,
        mapping: ColumnMapping,
        validation: ValidationSummary,
        raw_validation: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist metadata for downstream job processing."""
        metadata = {
            "fileId": file_id,
            "filename": filename,
            "mode": mode.value if isinstance(mode, ForecastMode) else mode,
            "schema_version": schema_version,
            "uploaded_at": datetime.utcnow().isoformat(),
            "mapping": mapping.dict(),
            "validation_summary": validation.dict(),
            "validation_raw": raw_validation,
        }
        metadata_path = self.metadata_dir / f"{file_id}.json"
        with metadata_path.open("w", encoding="utf-8") as fh:
            json.dump(metadata, fh, ensure_ascii=False, indent=2)

        # Keep a copy of the raw file for traceability
        raw_dir = self.raw_dir / file_id
        raw_dir.mkdir(parents=True, exist_ok=True)
        source_path = raw_dir / "source.csv"
        upload_path = self.get_file_path(file_id)
        try:
            source_path.write_bytes(upload_path.read_bytes())
        except Exception as exc:
            logger.warning("Failed to copy raw CSV for %s: %s", file_id, exc)

    def get_upload_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        metadata_path = self.metadata_dir / f"{file_id}.json"
        if not metadata_path.exists():
            return None
        with metadata_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

    def get_file_path(self, file_id: str) -> Path:
        return self.upload_dir / f"{file_id}.csv"

    def file_exists(self, file_id: str) -> bool:
        return self.get_file_path(file_id).exists()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def _detect_column_mapping(self, df: pd.DataFrame) -> ColumnMapping:
        mapping = ColumnMapping()

        lowercase_cols = {col.lower(): col for col in df.columns}

        def find_by_keywords(keywords: List[str]) -> Optional[str]:
            for keyword in keywords:
                for original_col in df.columns:
                    if keyword in original_col.lower():
                        return original_col
            return None

        mapping.date = self._first_datetime_column(df) or find_by_keywords(
            ["date", "day", "timestamp", "period"]
        )

        # Demand / quantity fields
        for keyword in ["demand", "units_sold", "qty", "quantity", "sales"]:
            if keyword in lowercase_cols:
                mapping.demand = lowercase_cols[keyword]
                break
        if not mapping.demand:
            numeric_candidates = df.select_dtypes(include=[np.number]).columns
            mapping.demand = numeric_candidates[0] if len(numeric_candidates) else None

        mapping.inventory = find_by_keywords(
            ["inventory", "on_hand", "stock", "available"]
        )
        mapping.lead_time = find_by_keywords(["lead_time", "leadtime", "lt"])
        mapping.sku = find_by_keywords(["sku", "product_id", "item", "product"])
        mapping.name = find_by_keywords(["name", "description", "title"])
        mapping.promo_flag = find_by_keywords(["promo", "promotion"])
        mapping.holiday_flag = find_by_keywords(["holiday"])

        return mapping

    def _first_datetime_column(self, df: pd.DataFrame) -> Optional[str]:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col
            try:
                pd.to_datetime(df[col].head())
                return col
            except Exception:
                continue
        return None

    def _detect_frequency(self, dates: pd.Series) -> Optional[str]:
        if dates.empty:
            return None
        normalized_dates = (
            pd.to_datetime(pd.Series(dates), errors="coerce")
            .dropna()
            .sort_values()
            .drop_duplicates()
        )
        if len(normalized_dates) < 3:
            return None

        day_values = normalized_dates.to_numpy(dtype="datetime64[D]")
        diffs = np.diff(day_values).astype(int)
        median_gap = np.median(diffs)

        if median_gap <= 1:
            return "D"
        if median_gap <= 8:
            return "W"
        if median_gap <= 32:
            return "M"
        return None

    def _compute_date_coverage(
        self, df: pd.DataFrame, mapping: ColumnMapping
    ) -> Optional[float]:
        if not mapping.date:
            return None
        dates = pd.to_datetime(df[mapping.date].dropna())
        if dates.empty:
            return None

        freq = self._detect_frequency(dates)
        if not freq:
            freq = "D"
        start, end = dates.min(), dates.max()
        expected = pd.date_range(start=start, end=end, freq=freq)
        if not len(expected):
            return None
        actual = dates.nunique()

        return round(actual / len(expected), 4)

    def _calculate_anomalies(
        self, df: pd.DataFrame, mapping: ColumnMapping
    ) -> List[ValidationAnomaly]:
        anomalies: List[ValidationAnomaly] = []
        if not mapping.demand or mapping.demand not in df.columns:
            return anomalies
        if not mapping.date:
            return anomalies

        working = df.copy()
        working = working.dropna(subset=[mapping.demand, mapping.date])
        if working.empty:
            return anomalies

        working[mapping.date] = pd.to_datetime(working[mapping.date])
        working["__sku__"] = (
            working[mapping.sku] if mapping.sku and mapping.sku in working.columns else "default_sku"
        )

        for sku, group in working.groupby("__sku__"):
            values = group[mapping.demand].astype(float)
            if len(values) < 10:
                continue
            mean = values.mean()
            std = values.std(ddof=0)
            if std == 0:
                continue
            z_scores = (values - mean) / std
            flagged = group.loc[np.abs(z_scores) >= 3.0]
            for _, row in flagged.iterrows():
                anomalies.append(
                    ValidationAnomaly(
                        unique_id=str(sku),
                        date=row[mapping.date].strftime("%Y-%m-%d"),
                        value=float(row[mapping.demand]),
                        z_score=float(((row[mapping.demand] - mean) / std)),
                    )
                )
        return anomalies

    def _build_validation_summary(
        self, df: pd.DataFrame, mapping: ColumnMapping
    ) -> ValidationSummary:
        coverage = self._compute_date_coverage(df, mapping)
        anomalies = self._calculate_anomalies(df, mapping)
        missing_by_field: Dict[str, float] = {}

        for field_name, column in [
            ("demand", mapping.demand),
            ("inventory", mapping.inventory),
            ("lead_time", mapping.lead_time),
        ]:
            if column and column in df.columns:
                missing_pct = float(df[column].isna().mean())
                missing_by_field[field_name] = round(missing_pct, 4)

        return ValidationSummary(
            rows=int(len(df)),
            columns=list(df.columns),
            detected_frequency=self._detect_frequency(
                pd.to_datetime(df[mapping.date], errors="coerce")
            )
            if mapping.date
            else None,
            date_coverage_pct=coverage,
            missing_by_field=missing_by_field,
            anomalies=anomalies,
        )

    def _extract_inventory_snapshot(
        self, df: pd.DataFrame, mapping: ColumnMapping
    ) -> Dict[str, float]:
        if not mapping.inventory or mapping.inventory not in df.columns:
            return {}
        date_col = mapping.date
        if date_col and date_col in df.columns:
            df = df.sort_values(date_col)
        sku_col = mapping.sku
        inventory_snapshot: Dict[str, float] = {}
        grouped = (
            df.groupby(sku_col)[mapping.inventory]
            if sku_col and sku_col in df.columns
            else {"default_sku": df[mapping.inventory]}
        )
        if isinstance(grouped, dict):
            series = grouped["default_sku"].dropna()
            if not series.empty:
                inventory_snapshot["default_sku"] = float(series.iloc[-1])
        else:
            for sku, series in grouped:
                series = series.dropna()
                if series.empty:
                    continue
                inventory_snapshot[str(sku)] = float(series.iloc[-1])
        return inventory_snapshot

    def _extract_lead_times(
        self,
        df: pd.DataFrame,
        mapping: ColumnMapping,
        default_lead_time: int,
    ) -> Dict[str, int]:
        sku_col = mapping.sku
        if mapping.lead_time and mapping.lead_time in df.columns:
            grouped = (
                df.groupby(sku_col)[mapping.lead_time]
                if sku_col and sku_col in df.columns
                else {"default_sku": df[mapping.lead_time]}
            )
            lead_times: Dict[str, int] = {}
            if isinstance(grouped, dict):
                series = grouped["default_sku"].dropna()
                if not series.empty:
                    lead_times["default_sku"] = int(series.iloc[-1])
                else:
                    lead_times["default_sku"] = default_lead_time
            else:
                for sku, series in grouped:
                    series = series.dropna()
                    lead_times[str(sku)] = (
                        int(series.iloc[-1])
                        if not series.empty
                        else int(default_lead_time)
                    )
            return lead_times

        if sku_col and sku_col in df.columns:
            unique_skus = df[sku_col].dropna().unique().tolist()
            return {str(sku): int(default_lead_time) for sku in unique_skus}

        return {"default_sku": int(default_lead_time)}

    def _write_frame(self, frame: pd.DataFrame, path: Path) -> None:
        try:
            frame.to_parquet(path, index=False)
        except Exception as exc:
            logger.warning(
                "Failed to write parquet %s (%s). Falling back to CSV.", path, exc
            )
            fallback_path = path.with_suffix(".csv")
            frame.to_csv(fallback_path, index=False)
