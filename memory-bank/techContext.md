# Tech Context: Inventra Technology Stack

## Technology Stack Overview

### Backend Technologies
- **Framework**: FastAPI (Python web framework)
- **Runtime**: Python 3.8+
- **ASGI Server**: Uvicorn with standard extras
- **Data Processing**: Pandas, NumPy
- **Forecasting**: StatsForecast (Nixtla library)
- **Validation**: Pydantic for data models
- **File Handling**: aiofiles for async file operations
- **Authentication**: python-jose, passlib (basic structure, not fully implemented)

### Frontend Technologies
- **Framework**: Next.js 15 (React-based)
- **Language**: TypeScript
- **Styling**: Tailwind CSS 4.x
- **UI Components**: shadcn/ui with Radix UI primitives
- **HTTP Client**: Axios
- **Charts**: Recharts for data visualization
- **CSV Parsing**: PapaParse
- **Date Handling**: date-fns
- **Icons**: Lucide React

### Development Tools
- **Linting**: ESLint with Next.js configuration
- **Type Checking**: TypeScript 5.x
- **Package Manager**: npm (frontend), pip (backend)
- **Version Control**: Git

## Development Environment Setup

### Prerequisites
- **Python**: 3.8 or higher
- **Node.js**: 18 or higher
- **npm**: Latest version
- **Git**: For version control

### Backend Setup Process
1. Navigate to `backend/` directory
2. Install dependencies: `pip install -r requirements.txt`
3. Run server: `python run_server.py` or `uvicorn main:app --host 0.0.0.0 --port 8000 --reload`
4. API available at `http://localhost:8000`
5. Auto-generated docs at `http://localhost:8000/docs`

### Frontend Setup Process
1. Navigate to `front-end/` directory
2. Install dependencies: `npm install`
3. Run development server: `npm run dev`
4. Application available at `http://localhost:3000`

### Development Workflow
- **Hot Reload**: Both backend and frontend support hot reload
- **API Documentation**: FastAPI auto-generates OpenAPI docs
- **Type Safety**: TypeScript provides compile-time type checking
- **Linting**: ESLint catches common issues
- **CORS**: Configured for local development (ports 3000, 8000)

## Key Dependencies Analysis

### Backend Dependencies
```
fastapi                    # Web framework
uvicorn[standard]         # ASGI server with extras
pandas                    # Data manipulation
numpy                     # Numerical computing
statsforecast            # Time series forecasting
pydantic                  # Data validation
python-multipart          # File upload support
python-jose[cryptography] # JWT handling
passlib[bcrypt]          # Password hashing
aiofiles                 # Async file operations
```

### Frontend Dependencies
```
next: 15.3.5             # React framework
react: ^19.0.0           # UI library
typescript: ^5           # Type system
tailwindcss: ^4.1.11     # CSS framework
axios: ^1.10.0           # HTTP client
recharts: ^3.0.2         # Charts library
papaparse: ^5.5.3        # CSV parsing
date-fns: ^4.1.0         # Date utilities
lucide-react: ^0.525.0   # Icons
```

### UI Component System
- **Base**: Radix UI primitives for accessibility
- **Styling**: Tailwind CSS with custom design system
- **Components**: shadcn/ui for consistent UI patterns
- **Customization**: class-variance-authority for component variants
- **Utilities**: clsx and tailwind-merge for class management

## Technical Constraints

### Performance Considerations
- **File Size Limits**: CSV files should be reasonably sized for memory processing
- **Processing Time**: Forecasting can take 10-30 seconds depending on data size
- **Memory Usage**: Pandas operations require sufficient RAM for large datasets
- **Concurrent Users**: Single-threaded processing may limit concurrent forecasts

### Data Format Requirements
- **CSV Format**: Standard comma-separated values
- **Required Columns**: Date column (various formats supported), numeric quantity column
- **Optional Columns**: Product ID for multi-product forecasting, product names
- **Date Formats**: Flexible parsing with pandas date inference
- **Encoding**: UTF-8 preferred, but system handles common encodings

### Browser Compatibility
- **Modern Browsers**: Chrome, Firefox, Safari, Edge (latest versions)
- **JavaScript**: ES2020+ features used
- **CSS**: Modern CSS features via Tailwind
- **File API**: HTML5 file upload capabilities required

## Configuration Management

### Environment Variables
- **Backend**: Port configuration, CORS origins, log levels
- **Frontend**: API base URL, build configuration
- **Development**: Hot reload settings, debug modes

### Build Configuration
- **Next.js**: TypeScript, Tailwind, ESLint integration
- **FastAPI**: Automatic OpenAPI generation, CORS middleware
- **Production**: Build optimization, static asset handling

## Deployment Architecture

### Local Development
- **Backend**: Direct Python execution with uvicorn
- **Frontend**: Next.js development server
- **Communication**: Direct HTTP between services
- **Storage**: Local file system for uploads and results

### Production Considerations
- **Process Management**: PM2, systemd, or Docker containers
- **Reverse Proxy**: Nginx for static assets and load balancing
- **SSL/TLS**: HTTPS termination at proxy level
- **Monitoring**: Application logs, health checks
- **Scaling**: Horizontal scaling possible due to stateless design

## Security Configuration

### CORS Policy
```python
allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"]
allow_credentials=True
allow_methods=["*"]
allow_headers=["*"]
```

### File Upload Security
- **Type Validation**: Only CSV files accepted
- **Size Limits**: Reasonable file size restrictions
- **Path Sanitization**: Secure file storage paths
- **Content Validation**: CSV structure validation

### API Security
- **Input Validation**: Pydantic models validate all inputs
- **Error Handling**: Safe error messages, no information disclosure
- **Rate Limiting**: Not implemented yet, but recommended for production
- **Authentication**: Basic structure exists but not fully implemented

## Testing Strategy

### Current State
- **No Automated Tests**: Testing is currently manual
- **Manual Testing**: Upload workflows, API endpoints, UI interactions

### Recommended Testing Approach
- **Backend**: pytest for API endpoints and services
- **Frontend**: Jest + React Testing Library for components
- **Integration**: End-to-end testing with Playwright or Cypress
- **API Testing**: Postman collections or automated API tests

## Monitoring and Logging

### Current Logging
- **Backend**: Python logging to stdout and app.log file
- **Frontend**: Browser console for client-side errors
- **Format**: Structured logging with timestamps and levels

### Production Monitoring Needs
- **Application Metrics**: Response times, error rates
- **System Metrics**: CPU, memory, disk usage
- **Business Metrics**: Forecast accuracy, user engagement
- **Alerting**: Error thresholds, performance degradation

## Development Best Practices

### Code Organization
- **Separation of Concerns**: Clear boundaries between layers
- **Type Safety**: TypeScript throughout frontend, Pydantic in backend
- **Error Handling**: Consistent error patterns across both services
- **Documentation**: Code comments and API documentation

### Version Control
- **Git Workflow**: Feature branches, clear commit messages
- **Repository Structure**: Monorepo with backend and frontend
- **Ignore Files**: Proper .gitignore for both Python and Node.js

### Performance Optimization
- **Frontend**: Code splitting, lazy loading, optimized builds
- **Backend**: Async operations, efficient data processing
- **Caching**: Opportunities for result caching and static assets
- **Database**: Future consideration for persistent storage
