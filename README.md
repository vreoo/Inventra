# Inventra - Inventory Prediction System

A comprehensive inventory prediction system that utilizes traditional time series algorithms and machine learning to provide highly useful information about item stock future recommendations and predictions.

## Features

- **Advanced Forecasting**: Uses StatsForecast library with multiple models (AutoARIMA, ETS, SeasonalNaive, etc.)
- **Real-time Processing**: Background job processing for forecast generation
- **Smart Data Validation**: Automatic CSV validation and column detection
- **Comprehensive Insights**: Stockout predictions, reorder points, seasonal analysis
- **Modern UI**: Next.js frontend with Tailwind CSS and shadcn/ui components
- **RESTful API**: FastAPI backend with proper error handling and logging

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
cd front-end
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

### 1. Prepare Your Data

Create a CSV file with inventory data. The system automatically detects columns, but recommended format:

```csv
date,product_id,quantity,product_name
2024-01-01,PROD001,150,Widget A
2024-01-02,PROD001,148,Widget A
...
```

**Required columns:**
- Date column (various formats supported)
- Numeric quantity column

**Optional columns:**
- Product ID for multi-product forecasting
- Product name for better labeling

### 2. Upload and Forecast

1. Go to `http://localhost:3000`
2. Upload your CSV file
3. Review the data preview and validation results
4. Click "Upload & Forecast" to start processing

### 3. View Results

The system provides:
- **Stockout predictions**: When inventory will run out
- **Reorder recommendations**: Optimal reorder points and dates
- **Seasonal insights**: Peak demand periods
- **Forecast accuracy**: Model performance metrics
- **Detailed forecasts**: Daily predictions with confidence intervals

## API Endpoints

### Upload
- `POST /api/upload` - Upload CSV file
- `GET /api/upload/{file_id}/validate` - Validate uploaded file

### Forecasting
- `POST /api/forecast` - Create forecast job
- `GET /api/forecast/{job_id}` - Get job status and results

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
