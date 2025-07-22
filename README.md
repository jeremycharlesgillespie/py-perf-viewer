# PyPerf Viewer

A Django web dashboard for visualizing and analyzing performance data collected by the [py-perf](https://pypi.org/project/py-perf-jg/) library.

Here's what you can expect when running the py-perf-viewer dashboard:

### Main Dashboard Home
![Main Dashboard](screenshots/01_dashboard_home.png)
*Overview of performance metrics with key statistics and recent activity*

### Performance Records List
![Performance Records](screenshots/02_performance_records.png)
*Paginated list of all performance records with filtering and sorting capabilities*

### Individual Record Detail
![Record Detail](screenshots/03_record_detail.png)
*Detailed view of a specific performance record showing function-level breakdown*

### Function Analysis View
![Function Analysis](screenshots/04_function_analysis.png)
*Cross-record analysis of specific functions with performance trends over time*

### REST API Endpoints

The dashboard also provides JSON API endpoints for programmatic access:

#### Performance Metrics API
`GET /api/metrics/` - Summary performance metrics in JSON format

```json
{
    "total_records": 2,
    "total_sessions": 2,
    "unique_hostnames": ["Mac.home.local"],
    "unique_functions": [
        "slow_io_operation",
        "cpu_intensive_task", 
        "check_aws_credentials",
        "mixed_workload",
        "fast_calculation",
        "variable_duration"
    ],
    "avg_session_duration": 0.0,
    "slowest_functions": [
        ["check_aws_credentials", 0.294],
        ["slow_io_operation", 0.105],
        ["mixed_workload", 0.055]
    ],
    "most_active_hosts": [
        ["Mac.home.local", 14]
    ]
}
```

#### Hostnames API
`GET /api/hostnames/` - List of unique hostnames for filtering

```json
{
    "hostnames": ["Mac.home.local"]
}
```

#### Functions API
`GET /api/functions/` - List of unique function names for analysis

```json
{
    "functions": [
        "check_aws_credentials",
        "cpu_intensive_task",
        "fast_calculation",
        "mixed_workload", 
        "slow_io_operation",
        "variable_duration"
    ]
}
```

## Features

- **Performance Overview**: Dashboard showing key metrics and trends
- **Function Analysis**: Detailed analysis of individual function performance
- **Record Browser**: Browse and filter performance records
- **REST API**: Programmatic access to performance data
- **Real-time Data**: Automatically displays latest performance data from DynamoDB or local storage

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install requirements
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### 2. Configure PyPerf

Create a `.py-perf.yaml` configuration file in the project root:

```yaml
py_perf:
  enabled: true

# For local development (no AWS required)
local:
  enabled: true
  data_dir: "./perf_data"
  format: "json"

# For production with AWS DynamoDB
# aws:
#   region: "us-east-1"
#   table_name: "py-perf-data"
```

### 3. Start the Dashboard

```bash
./start_viewer.py
```

Visit http://localhost:8000 to view the performance dashboard.

## Integration with PyPerf Core Library

This dashboard works with data collected by the [py-perf](https://pypi.org/project/py-perf-jg/) core library:

```python
from py_perf import PyPerf

# Initialize performance tracking
perf = PyPerf()

@perf.time_it
def my_function():
    # Your application code
    pass

# Data is automatically collected and can be viewed in this dashboard
```

## Project Structure

```
py-perf-viewer/
├── pyperfweb/              # Django project
│   ├── dashboard/          # Main dashboard app
│   │   ├── views.py       # Dashboard views
│   │   ├── models.py      # Data models
│   │   ├── services.py    # DynamoDB service
│   │   ├── templates/     # HTML templates
│   │   └── tests.py       # Unit tests
│   ├── settings.py        # Django settings
│   └── urls.py            # URL configuration
├── manage.py              # Django management
├── requirements.txt       # Production dependencies
└── requirements-dev.txt   # Development dependencies
```

## Development

### Running Tests

```bash
# Unit tests (quiet mode, recommended)
python manage.py test pyperfweb.dashboard.tests --settings=pyperfweb.test_settings

# Unit tests (verbose mode, for debugging)
python manage.py test pyperfweb.dashboard.tests

# Integration tests (requires running Django server)
python test_django_server.py
```

### Code Quality

```bash
# Format code
black pyperfweb/
isort pyperfweb/

# Lint code  
flake8 pyperfweb/
mypy pyperfweb/
```

## Configuration

The dashboard uses the same configuration system as the core py-perf library. See the [py-perf documentation](https://github.com/jeremycharlesgillespie/py-perf) for detailed configuration options.

## API Endpoints

- `GET /api/metrics/` - Performance metrics summary
- `GET /api/hostnames/` - List of unique hostnames
- `GET /api/functions/` - List of unique function names
- `GET /records/` - Browse performance records
- `GET /functions/{name}/` - Function-specific analysis

## Deployment

### Docker (Recommended)

```bash
# Build Docker image
docker build -t py-perf-viewer .

# Run with environment variables
docker run -p 8000:8000 \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e DYNAMODB_TABLE_NAME=py-perf-data \
  py-perf-viewer
```

### Traditional Deployment

1. Set up a production WSGI server (gunicorn, uWSGI)
2. Configure static file serving
3. Set up database (if using Django models)
4. Configure environment variables for AWS access

## Related Projects

- **[py-perf](https://pypi.org/project/py-perf-jg/)** - Core performance tracking library
- **[py-perf GitHub](https://github.com/jeremycharlesgillespie/py-perf)** - Core library source code

## License

MIT License - see LICENSE file for details.