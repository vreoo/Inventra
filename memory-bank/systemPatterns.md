# System Patterns: Inventra Architecture

## Overall Architecture

### System Design Pattern
**Microservices Architecture** with clear separation of concerns:
- **Frontend**: Next.js React application (Port 3000)
- **Backend**: FastAPI Python service (Port 8000)
- **Communication**: RESTful API with JSON payloads
- **Storage**: File-based storage for uploads and results

### Key Architectural Decisions

#### 1. API-First Design
- Backend exposes RESTful endpoints
- Frontend consumes API through dedicated service layer
- Clear contract between frontend and backend
- Enables future integrations and mobile apps

#### 2. Async Processing Pattern
- File uploads are processed immediately
- Forecast generation runs as background jobs
- Real-time status updates via polling
- Prevents UI blocking on long-running operations

#### 3. Stateless Services
- No session state stored on server
- Each request contains all necessary information
- Enables horizontal scaling if needed
- Simplifies deployment and maintenance

## Backend Patterns

### Directory Structure
```
backend/
├── main.py              # FastAPI app initialization
├── api/                 # API route handlers
│   ├── upload.py        # File upload endpoints
│   └── forecast.py      # Forecasting endpoints
├── models/              # Pydantic data models
├── services/            # Business logic layer
│   ├── file_handler.py  # File processing
│   └── forecast_engine.py # Forecasting logic
└── storage/             # File storage directory
```

### Service Layer Pattern
- **Separation of Concerns**: API routes delegate to service classes
- **Business Logic Isolation**: Core logic separated from HTTP concerns
- **Testability**: Services can be unit tested independently
- **Reusability**: Services can be used by multiple API endpoints

### Data Validation Pattern
- **Pydantic Models**: Strong typing and automatic validation
- **Request/Response Models**: Clear API contracts
- **Error Handling**: Consistent error responses across endpoints
- **Data Transformation**: Automatic serialization/deserialization

### Forecasting Engine Pattern
- **Strategy Pattern**: Multiple forecasting models (AutoARIMA, ETS, etc.)
- **Factory Pattern**: Model selection based on configuration
- **Pipeline Pattern**: Data preprocessing → Model fitting → Post-processing
- **Error Recovery**: Fallback models if primary model fails

## Frontend Patterns

### Directory Structure
```
front-end/src/
├── app/                 # Next.js App Router
│   ├── page.tsx         # Home page
│   ├── upload/          # Upload workflow
│   ├── results/         # Results display
│   ├── settings/        # Configuration
│   └── api/             # API route handlers
├── components/          # Reusable UI components
│   ├── ui/              # shadcn/ui components
│   ├── Upload/          # Upload-specific components
│   └── Settings/        # Settings components
├── services/            # API client layer
└── lib/                 # Utility functions
```

### Component Architecture
- **Atomic Design**: Small, reusable components
- **Container/Presenter**: Smart components handle logic, dumb components handle display
- **Custom Hooks**: Reusable state logic
- **TypeScript**: Strong typing throughout

### State Management Pattern
- **React State**: Local component state for UI interactions
- **Server State**: API responses cached and managed
- **Form State**: Controlled components with validation
- **No Global State**: Keeping it simple with prop drilling and context where needed

### API Client Pattern
- **Service Layer**: Centralized API calls in `services/api.ts`
- **Error Handling**: Consistent error handling across all API calls
- **Type Safety**: TypeScript interfaces for all API responses
- **Axios Integration**: HTTP client with interceptors

## Data Flow Patterns

### Upload Workflow
1. **File Selection**: User selects CSV file
2. **Client Validation**: Basic file type/size checks
3. **Upload**: File sent to `/api/upload` endpoint
4. **Server Validation**: Detailed CSV parsing and validation
5. **Preview**: User reviews detected columns and data sample
6. **Confirmation**: User confirms settings and starts forecast

### Forecast Workflow
1. **Job Creation**: POST to `/api/forecast` creates background job
2. **Status Polling**: Frontend polls `/api/forecast/{job_id}` for updates
3. **Processing**: Backend runs forecasting models
4. **Results Storage**: Results saved to file system
5. **Completion**: Status updated, results available for retrieval

### Error Handling Pattern
- **Graceful Degradation**: System continues working with partial failures
- **User-Friendly Messages**: Technical errors translated to user language
- **Logging**: Comprehensive logging for debugging
- **Recovery**: Clear paths for users to retry failed operations

## Integration Patterns

### CORS Configuration
- Specific origins allowed (localhost:3000, 127.0.0.1:3000)
- All methods and headers permitted for development
- Credentials support enabled

### File Storage Pattern
- **Local File System**: Simple file-based storage
- **Organized Structure**: Files organized by upload ID and job ID
- **Cleanup Strategy**: (Not yet implemented) - potential for file cleanup jobs

### Model Integration
- **StatsForecast Library**: Primary forecasting engine
- **Pandas Integration**: Data manipulation and preprocessing
- **NumPy Support**: Numerical computations
- **Multiple Model Support**: Easy to add new forecasting models

## Security Patterns

### Input Validation
- **File Type Validation**: Only CSV files accepted
- **Size Limits**: Reasonable file size restrictions
- **Content Validation**: CSV structure and data type validation
- **Sanitization**: Input cleaning to prevent injection attacks

### Error Information Disclosure
- **Safe Error Messages**: No sensitive information in error responses
- **Logging**: Detailed errors logged server-side only
- **Status Codes**: Appropriate HTTP status codes for different scenarios

## Performance Patterns

### Async Processing
- **Background Jobs**: Long-running forecasts don't block API
- **Non-blocking I/O**: FastAPI async/await patterns
- **Efficient Data Processing**: Pandas vectorized operations
- **Memory Management**: Streaming file processing where possible

### Caching Strategy
- **No Caching Yet**: Simple implementation for now
- **Future Opportunities**: Model results, validation results, static assets

## Deployment Patterns

### Development Setup
- **Separate Processes**: Backend and frontend run independently
- **Hot Reload**: Both services support development hot reload
- **Port Configuration**: Standard ports (3000, 8000) for easy development
- **Environment Variables**: Configuration through environment variables

### Production Considerations
- **Process Management**: Both services need process managers
- **Reverse Proxy**: Nginx or similar for production deployment
- **Static Assets**: Frontend build artifacts need serving
- **Logging**: Structured logging for production monitoring
