# Demand-Driven Planning Specification

## Overview

Inventra is expanding from stock-on-hand projections to a demand-driven
planning workflow while keeping the legacy inventory forecast experience
available. This document specifies the revised end-to-end flow across the
FastAPI backend and the Next.js frontend.

The design preserves the existing CSV upload experience (single file) but
expects richer columns describing demand history, current inventory, and lead
times. A feature flag (`demand_planning_enabled`) gates the new behaviour so
legacy inventory jobs can continue to run unchanged.

## Feature Flag & Modes

| Field | Description |
| --- | --- |
| `mode` | `inventory` (default) or `demand`. Controls processing pipeline. |
| `schema_version` | Semantic version string (e.g. `1.0.0`). Stored with every job manifest. |
| `demand_planning_enabled` | Boolean flag in frontend + backend config deciding which mode to offer. |

The upload flow inspects the flag and default mode. Users can explicitly select
`inventory` to run the legacy pipeline even when demand planning is enabled.

## Upload & Mapping Workflow

1. **Single CSV Upload** (no zip/bundle).
2. **Auto Detection** via heuristics:
   - Demand quantity columns (`demand_qty`, `units_sold`, etc.).
   - Current stock columns (`on_hand`, `stock_qty`).
   - Lead time columns (`lead_time_days`, `lt`).
   - SKU/product identifiers and names.
   - Date columns (daily/weekly history).
3. **Mapping Wizard** allows manual overrides and shows coverage diagnostics
   (missing values, duplicated dates, gaps).
4. **Validation Summary** reports:
   - Date coverage by SKU.
   - Percentage of missing demand/stock/lead time.
   - Frequency detection (`D` or `W`).
   - Anomalies (z-score > 3 by default) flagged per SKU.
5. **Persistence**:
   - Raw CSV stored in `storage/raw/{jobId}/source.csv`.
   - Column mapping JSON stored alongside `mapping.json`.
   - Processed parquet tables written to
     `storage/processed/{jobId}/{series}.parquet` where `{series}` is one of
     `demand`, `inventory`, `lead_time`, `events`.
   - Job manifest located at `storage/jobs/{jobId}.json` now includes mode,
     schema version, and validation metadata.

## Data Model Additions

### Processed Demand Series (`demand.parquet`)

| Column | Type | Notes |
| --- | --- | --- |
| `unique_id` | string | SKU identifier. |
| `ds` | datetime | Truncated to day/week start based on detected frequency. |
| `y` | float | Demand quantity for the period. |
| `source_qty` | float | Raw quantity prior to aggregation. |
| `coverage_flag` | bool | True if derived from complete period data. |

### Inventory Snapshot (`inventory.parquet`)

| Column | Type | Notes |
| --- | --- | --- |
| `unique_id` | string | SKU identifier. |
| `snapshot_date` | datetime | Defaults to upload date. |
| `on_hand` | float | Current available stock. |

### Lead Times (`lead_time.parquet`)

| Column | Type | Notes |
| --- | --- | --- |
| `unique_id` | string | SKU identifier. |
| `lead_time_days` | int | Fixed days per SKU. |
| `source` | string | `"file"` or `"default"`. |

### Config History (`storage/configs/…`)

- `config_history.jsonl`: append-only log containing records:
  ```json
  {
    "timestamp": "2025-01-09T15:04:05Z",
    "version": "1.2.0",
    "scope": "global" | "sku",
    "target": null | "SKU123",
    "settings": {
      "service_level": 0.95,
      "lead_time_days": 7,
      "safety_stock_policy": "z_score"
    },
    "author": "admin@example.com"
  }
  ```
- `latest.json`: snapshot of currently effective merged config (global +
  overrides).

## Backend Services

### Upload API (`POST /api/upload`)

**Request**: multipart/form-data with CSV file. Optional query/body fields:

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `mode` | string | `"inventory"` | `inventory` or `demand`. |
| `schema_version` | string | `"1.0.0"` | Pinned by frontend constant. |

**Response**:
```json
{
  "fileId": "f5dd…",
  "filename": "upload.csv",
  "mode": "demand",
  "schema_version": "1.0.0",
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": [],
    "info": {
      "rows": 650,
      "columns": ["date", "sku", …],
      "detected_frequency": "D",
      "date_coverage_pct": 0.94,
      "missing_by_field": {
        "demand": 0.0,
        "lead_time": 0.05,
        "inventory": 0.0
      },
      "anomalies": [
        {
          "unique_id": "SKU123",
          "date": "2024-11-26",
          "value": 400,
          "z_score": 3.2
        }
      ]
    }
  },
  "mapping": {
    "date": "date",
    "sku": "product_id",
    "demand": "units_sold",
    "inventory": "on_hand",
    "lead_time": "lead_time_days",
    "name": "product_name"
  }
}
```

### Forecast Jobs (`POST /api/forecast`)

**Request**:
```json
{
  "fileId": "f5dd…",
  "mode": "demand",
  "config": {
    "model": "AutoARIMA",
    "horizon": 45,
    "frequency": "D",
    "confidence_level": 0.95,
    "service_level": 0.9,
    "lead_time_days_default": 7,
    "safety_stock_policy": "ss_z_score",
    "reorder_policy": "continuous_review"
  }
}
```

**Processing Flow (mode = demand)**:

1. Load mapping + processed parquet from storage.
2. Rebuild demand series per SKU, filling gaps with interpolation or zero
   (configurable).
3. Select model:
   - Default cascade: AutoARIMA → AutoETS → SeasonalNaive.
   - For intermittent series, fallback to CrostonClassic or CrostonSBA.
   - Optional TBATS when package installed (`from tbats import TBATS`).
4. Call `StatsForecast(...).forecast` with `level=[80, 95]` intervals.
5. Compute safety stock using `service_level` → z-score (via `scipy.stats`
   normal quantile) against historical demand std and lead time.
6. Simulate on-hand depletion:
   ```text
   available_today = on_hand
   for each day:
       demand = forecast
       available_today -= demand
       if available_today <= reorder_point and reorder not yet placed:
           reorder_date = current_day
           reorder_qty = max(
               target_cycle_stock - available_today,
               min_order_qty (optional future feature)
           )
       if available_today <= 0: stockout_date = current_day
   ```
7. Write results back to job manifest:
   ```json
   {
     "product_id": "SKU123",
     "forecast_points": [
       {"date": "2025-02-01", "forecast": 42, "lower_bound": 30, "upper_bound": 55},
       …
     ],
     "stockout_date": "2025-02-11",
     "reorder_point": 120,
     "reorder_date": "2025-02-05",
     "recommended_order_qty": 380,
     "service_level": 0.9,
     "lead_time_days": 7,
     "model_used": "AutoARIMA",
     "safety_stock": 75,
     "insights": [
       {"type": "stockout_risk", "severity": "critical", "message": "Projected stockout in 9 days"}
     ],
     "accuracy_metrics": { "RMSE": 18.4, "MAPE": 6.1 }
   }
   ```

### Config Service (`/api/configs`)

- `GET /api/configs`: returns merged `latest.json`.
- `POST /api/configs`: accepts payload with optional `target` (SKU) and writes
  new record to `config_history.jsonl`, updates snapshot, and bumps version.
- `GET /api/configs/history`: streams JSON lines for auditing.

## Frontend Changes

### Upload Wizard (Next.js)

1. **Step 1**: Upload file (existing UI updates copy to mention demand data).
2. **Step 2**: Column mapping UI
   - Dropdowns for `Demand quantity`, `Current stock`, `Lead time (days)`, `SKU`,
     `Product name`, `Date`.
   - Live preview per SKU.
   - Validation metrics displayed in an alert panel.
3. **Step 3**: Configuration picker
   - Global defaults: service level slider, lead time default, reorder policy.
   - Per-SKU overrides table (editable lead times).
   - Toggle to run in legacy mode.
4. **Submission**: creates forecast job with selected mode + config.

### Results Page

- Status indicator unchanged.
- For demand mode jobs:
  - Dual chart: historical demand vs. forecast + prediction intervals.
  - Secondary chart: projected inventory depletion vs. reorder point.
  - Metrics cards: `Reorder Date`, `Recommended Order Qty`, `Safety Stock`,
    `Service Level`.
  - Download button exporting CSV of recommended orders.
  - Validation summary section showing coverage/anomaly statistics.

### Feature Flag Handling

- Frontend env var `NEXT_PUBLIC_DEMAND_PLANNING_ENABLED` toggles new wizard
  sections.
- Backend uses environment variable `DEMAND_PLANNING_ENABLED` (default `false`).
  When false, upload defaults to `inventory` mode and hides demand-specific
  config in responses.

## Testing Strategy

1. **Backend Unit Tests**
   - Column detection + mapping fallback cases.
   - Validation metrics (coverage, anomaly detection).
   - Forecast engine selection logic (ARIMA vs. Croston vs. TBATS).
   - Safety stock and reorder simulation calculations.
   - Config service append-only guarantees.
2. **Backend Integration Tests**
   - Upload → Process → Forecast job end-to-end with sample dataset.
   - Feature flag toggling ensures legacy mode unaffected.
3. **Frontend Tests**
   - React Testing Library for wizard navigation, mapping persistence, config
     updates.
   - Rendering of demand vs. inventory charts with sample API responses.
4. **Datasets**
   - `sample_data/demand_planning_example.csv` used in tests + docs.
   - Legacy `sample_inventory_data.csv` retained for regression tests.

## Monitoring & Rollout

- Feature flag initially off; expose to staging first.
- Add structured logs when demand pipeline runs (`mode=demand`, SKU counts,
  duration).
- Track validation error rates to catch schema issues.
- Migration note in README on how to convert existing CSVs to include demand,
  lead time, and inventory columns.

## Open Items (Future Enhancements)

- Interpret promo/holiday flags for uplift adjustments.
- Multi-facility support with location column and separate policies.
- Vendor-based lead time variability and probabilistic safety stock.
- Calendar integrations for public holidays.

---

Document owner: Codex (GPT-5)  
Last updated: 2025-01-09
