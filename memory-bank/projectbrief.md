# Project Brief: Inventra - Inventory Prediction System

## Project Overview
Inventra is a comprehensive inventory prediction system that combines traditional time series algorithms with machine learning to provide actionable insights for inventory management. The system helps businesses predict future stock levels, identify potential stockouts, and optimize reorder points.

## Core Requirements

### Primary Goals
1. **Accurate Forecasting**: Provide reliable inventory predictions using multiple forecasting models
2. **Ease of Use**: Simple CSV upload interface with automatic data validation
3. **Real-time Processing**: Background job processing for forecast generation
4. **Actionable Insights**: Clear recommendations for reorder points and stockout prevention
5. **Scalability**: Handle multiple products and large datasets efficiently

### Key Features
- **Multi-Model Forecasting**: AutoARIMA, ETS, SeasonalNaive, Naive, RandomWalkWithDrift
- **Smart Data Validation**: Automatic CSV column detection and validation
- **Comprehensive Analytics**: Stockout predictions, seasonal analysis, confidence intervals
- **Modern Web Interface**: Responsive design with real-time status updates
- **RESTful API**: Well-documented API for integration capabilities

### Technical Requirements
- **Backend**: FastAPI with Python 3.8+
- **Frontend**: Next.js 15 with TypeScript
- **Forecasting Engine**: StatsForecast library (Nixtla)
- **Data Processing**: Pandas and NumPy for data manipulation
- **UI Framework**: Tailwind CSS with shadcn/ui components

### Success Criteria
1. Users can upload CSV files and receive forecasts within reasonable time
2. System provides accurate predictions with confidence intervals
3. Interface is intuitive and requires minimal training
4. API is stable and well-documented for potential integrations
5. System handles various data formats and edge cases gracefully

### Constraints
- Must work with standard CSV formats
- Forecasting horizon: 1-365 days
- Support for daily, weekly, and monthly data frequencies
- Confidence levels between 0.5-0.99
- Local deployment (no cloud dependencies required)

## Project Scope
- **In Scope**: CSV upload, data validation, forecasting, results visualization, API endpoints
- **Out of Scope**: Real-time data streaming, database persistence, user authentication (basic structure exists but not fully implemented), multi-tenant support

## Target Users
- Inventory managers
- Supply chain analysts
- Small to medium business owners
- Data analysts working with inventory data
