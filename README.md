# Inventra - Inventory Prediction System

A comprehensive inventory prediction system that utilizes traditional time series algorithms and machine learning to provide highly useful information about item stock future recommendations and predictions.

## Features

- **Demand-Driven Planning (New)**: Forecast demand, simulate depletion, and recommend reorder quantities with safety stock policies.
- **Advanced Forecasting**: Uses StatsForecast library with multiple models (AutoARIMA, ETS, SeasonalNaive, Croston variants, optional TBATS).
- **Real-time Processing**: Background job processing for forecast generation.
- **Smart Data Validation**: Automatic CSV validation, column detection, coverage checks, and anomaly detection.
- **Config Versioning**: Append-only configuration history with global and per-SKU overrides.
- **Modern UI**: Next.js frontend featuring mapping wizard, policy controls, and enriched result visualisations.
- **RESTful API**: FastAPI backend with structured logging and error handling.

## Architecture

### Backend (FastAPI)
- **API Layer**: RESTful endpoints for file upload and forecast management
- **Services**: File handling, forecast engine with StatsForecast integration
- **Models**: Pydantic models for data validation and serialization
- **Background Jobs**: Async processing for forecast generation

### Frontend (Next.js)
- **Upload Interface**: CSV file upload with preview and validation
- **Results Dashboard**: Real-time job status and comprehensive forecast results
- **Responsive Design**: Mobile-friendly interface with Tailwind CSS

## Quick Start

### Prerequisites
- Python 3.8+
- Node.js 18+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Run the startup script (installs dependencies and starts server):
```bash
python run_server.py
```

Or manually:
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
pnpm install # or npm install / yarn install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

> **Feature flags**  
> Demand planning is gated behind environment flags. Set `DEMAND_PLANNING_ENABLED=true` for the API and `NEXT_PUBLIC_DEMAND_PLANNING_ENABLED=true` for the frontend to expose the new workflow. Leave both false to continue using the legacy inventory mode.

## Usage

### 1. Prepare Your Data

Demand planning accepts a single CSV containing demand history, current stock, and lead times. Auto-mapping suggests columns, and you can override selections in the UI.

**Recommended schema**

```csv
date,sku,demand_units,on_hand,lead_time_days,product_name
2024-10-01,SKU-100,42,320,7,Essential Widgets
2024-10-02,SKU-100,38,320,7,Essential Widgets
```

- `date` (required): daily or weekly timestamps.
- `demand_units` (required): quantity consumed or sold.
- `sku` (optional, recommended): unique product identifier.
- `on_hand` (optional): current inventory snapshot; defaults to 0 if missing.
- `lead_time_days` (optional): SKU-specific lead time; defaults to global setting.
- `product_name` (optional): label used in the UI.

A sample dataset is available at `sample_data/demand_planning_example.csv`.

### 2. Upload and Forecast

1. Go to `http://localhost:3000`
2. Choose demand or legacy inventory mode (demand planning requires enabling the feature flag).
3. Upload your CSV file and review detected mappings, validation feedback, and policy settings.
4. Adjust service-level, lead-time defaults, and safety stock rules if needed.
5. Run the forecast to trigger background processing.

### 3. View Results

Output includes:
- **Demand forecast**: Time series with prediction intervals per SKU.
- **Reorder simulation**: Recommended order date/quantity, reorder point, safety stock.
- **Stock risk flags**: Projected stockout dates and service-level coverage.
- **Validation summary**: Coverage metrics, anomalies, detected frequency.
- **Legacy insights**: Inventory forecasts remain available via inventory mode.

## API Endpoints

### Upload
- `POST /api/upload` — Upload CSV file, returns mapping + validation summary.
- `GET /api/upload/{file_id}/validate` — Retrieve validation + mapping for existing upload.

### Forecasting
- `POST /api/forecast` — Create a forecast job (supports `mode` + `mapping_overrides`).
- `GET /api/forecast/{job_id}` — Get job status, results, and validation metadata.

### Configuration
- `GET /api/configs` — Fetch the latest merged configuration.
- `POST /api/configs` — Append a versioned configuration update.
- `GET /api/configs/history` — Stream historical configuration records.

### Health
- `GET /` - API status
- `GET /health` - Health check

## Configuration

### Forecast Models
- **AutoARIMA**: Automatic ARIMA model selection (default)
- **ETS**: Exponential smoothing
- **SeasonalNaive**: Seasonal naive forecasting
- **Naive**: Simple naive forecasting
- **RandomWalkWithDrift**: Random walk with drift

### Parameters
- **Horizon**: Forecast period (1-365 days, default: 30)
- **Frequency**: Data frequency (D=daily, W=weekly, M=monthly)
- **Confidence Level**: Prediction intervals (0.5-0.99, default: 0.95)
- **Seasonal Length**: Custom seasonal period

## Sample Data

A sample CSV file (`sample_inventory_data.csv`) is included in the root directory for testing.

## Development

### Project Structure
```
Inventra/
├── backend/
│   ├── api/           # API endpoints
│   ├── models/        # Pydantic models
│   ├── services/      # Business logic
│   ├── storage/       # File storage
│   └── main.py        # FastAPI app
├── front-end/
│   ├── src/
│   │   ├── app/       # Next.js pages
│   │   ├── components/ # React components
│   │   └── services/  # API client
│   └── package.json
└── README.md
```

### Key Technologies
- **Backend**: FastAPI, StatsForecast, Pandas, Pydantic
- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui
- **Data Processing**: Pandas, NumPy
- **Forecasting**: StatsForecast (Nixtla)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions, please create an issue in the GitHub repository.
