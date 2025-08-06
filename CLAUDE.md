# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

py-perf-viewer is a Django web dashboard for visualizing performance data from the py-perf library. It displays performance metrics through a web UI and REST API, using DynamoDB for production or local JSON files for development. Always use the virtual environment when running python commands. At the end of any operation, always recheck the README.md to see if it needs to be updated also. 

Do not mention claude or co-pilot in commit messages.

## Virtual Environment Usage
ALWAYS use the virtual environment for any pip or python commands. Never use the system Python installation.
## Development Commands

### Setup
```bash
# Install dependencies (production)
pip install -r requirements.txt

# Install development dependencies  
pip install -r requirements-dev.txt

# Or install with dev extras
pip install -e ".[dev]"

# Quick start (automated setup with collectstatic)
python start_viewer.py
```

### Django Commands
```bash
# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Start development server
python manage.py runserver 8000

# Run Django shell
python manage.py shell
```

### Testing
```bash
# Unit tests (Django test suite) - quiet mode
python manage.py test pyperfweb.dashboard.tests --settings=pyperfweb.test_settings

# Unit tests (Django test suite) - verbose mode
python manage.py test pyperfweb.dashboard.tests

# Unit tests (pytest)
pytest

# Integration tests (requires running server)
python test_django_server.py

# Test with coverage
pytest --cov=pyperfweb
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

## Architecture

### Core Structure
- **pyperfweb/dashboard/**: Main Django app containing all functionality
- **pyperfweb/settings.py**: Django config with PyPerf integration
- **start_viewer.py**: Automated setup and startup script
- **test_django_server.py**: Integration test suite

### Data Layer
- **No Django ORM models** - uses dataclasses (`PerformanceRecord`, `PerformanceMetrics`)
- **DynamoDBService** (`services.py`): Handles all AWS DynamoDB operations
- **External data sources**: DynamoDB (production) or local JSON files (development)

### Key Components
- **Views** (`views.py`): Dashboard, record browser, function analysis, REST API
- **Templates**: Bootstrap-based responsive UI with filtering and pagination  
- **Configuration**: Integrates with py-perf's `.py-perf.yaml` config system

### URL Structure
```
/                           # Main dashboard
/records/                   # Performance records list
/records/<record_id>/       # Individual record details  
/functions/<function_name>/ # Function analysis across records
/api/metrics/              # REST API endpoints
/api/hostnames/
/api/functions/
```

## Configuration

### PyPerf Configuration
The dashboard reads from `.py-perf.yaml`, `py-perf.yaml`, or `~/.py-perf.yaml`:

```yaml
py_perf:
  enabled: true

# Development mode
local:
  enabled: true
  data_dir: "./perf_data"
  format: "json"

# Production mode  
# aws:
#   region: "us-east-1"
#   table_name: "py-perf-data"
```

### Development vs Production
- **Development**: Uses local JSON files, no AWS credentials needed
- **Production**: Requires AWS credentials and DynamoDB table access

## Testing Strategy

### Unit Tests
- Located in `pyperfweb/dashboard/tests.py`
- Mock DynamoDB service for offline testing
- Test models, views, and API endpoints

### Integration Tests  
- `test_django_server.py` tests the full running server
- Tests all endpoints with real HTTP requests
- Validates JSON API responses

### Test Data
- Uses Factory Boy for generating test data
- Mock data structures match real PyPerf performance records

## Dependencies

### Core
- **Django 4.2+**: Web framework
- **Django REST Framework**: API functionality
- **py-perf-jg**: Core performance library integration
- **boto3**: AWS SDK for DynamoDB

### Development
- **pytest**: Testing framework
- **black/isort**: Code formatting
- **flake8/mypy**: Linting and type checking
- **factory-boy**: Test data generation

## Key Development Notes

- **Service Layer Pattern**: All data access goes through `DynamoDBService`
- **Dataclass Models**: Uses `@dataclass` instead of Django models
- **External Data**: No local database storage, reads from DynamoDB/files
- **Configuration Display**: Settings show detected PyPerf config on startup
- **Error Handling**: Comprehensive 404 and error templates
- **Responsive Design**: Bootstrap-based mobile-friendly interface