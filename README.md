# AI Test Platform

AI-powered test automation platform with LLM test case generation, API/iOS test execution, and comprehensive report generation.

## Features

- **AI Test Case Generation** - Generate test cases from requirements or API specs using LLM
- **API Test Automation** - Execute HTTP tests with JSONPath assertions and variable chaining
- **iOS Test Automation** - Generate XCUITest code and run on iOS Simulator
- **Report Generation** - HTML, Markdown, and JSON reports with detailed analytics
- **Web API** - RESTful API with Swagger UI documentation
- **Document Parsing** - Support for Swagger, OpenAPI, and requirement documents

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/lukysmile2025-crypto/AI-Test-Platform.git
cd AI-Test-Platform

# Install dependencies
pip install -r requirements.txt

# Configure environment (optional - for AI generation)
cp .env.example .env
# Edit .env and add your LLM API key
```

### Run API Server

```bash
# Start the server
python -m uvicorn api.app:app --reload

# Open Swagger UI
open http://localhost:8000/docs
```

### Run API Tests (CLI)

```python
from core.test_runner import TestRunner, TestRunConfig

# Configure
config = TestRunConfig(
    output_dir="./test_output",
    api_base_url="https://api.example.com",
)

runner = TestRunner(config=config)

# Define test cases
test_cases = {
    "api_name": "My API",
    "test_cases": [
        {
            "id": "TC_001",
            "title": "Get User",
            "method": "GET",
            "endpoint": "/users/1",
            "expected_status": 200,
            "expected_response": {
                "assertions": [
                    {"path": "$.id", "operator": "equals", "value": 1}
                ]
            }
        }
    ]
}

# Execute
result = runner.run_api_tests(test_cases)
print(f"Pass rate: {result.pass_rate}%")
```

### Run Example Test

```bash
# Test against JSONPlaceholder API
python test_real_api.py
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info |
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| POST | `/api/v1/test-cases/generate/requirement` | Generate from requirement |
| POST | `/api/v1/test-cases/generate/api` | Generate from API spec |
| POST | `/api/v1/api-test/execute/sync` | Execute API tests |
| GET | `/api/v1/api-test/results` | List test results |

## Project Structure

```
AI-Test-Platform/
├── api/                    # FastAPI web server
│   ├── app.py             # Main application
│   └── routes/            # API endpoints
├── core/                   # Core services
│   ├── llm_client.py      # LLM API client
│   ├── test_case_service.py
│   └── test_runner.py     # Unified test runner
├── executors/              # Test execution
│   ├── api_executor.py    # HTTP test executor
│   └── ios_executor.py    # iOS simulator executor
├── prompts/                # LLM prompts
│   ├── prompt_manager.py  # Prompt orchestration
│   ├── test_case_generator.py
│   ├── ios_simulator_test.py
│   └── system_prompts.py
├── reporters/              # Report generation
│   ├── api_reporter.py    # API test reports
│   ├── ios_reporter.py    # iOS test reports
│   └── html_reporter.py   # Dashboard
├── parsers/                # Document parsing
│   ├── swagger_parser.py
│   ├── openapi_parser.py
│   └── requirement_parser.py
├── storage/                # Data persistence
├── config/                 # Configuration
├── utils/                  # Utilities
└── examples/               # Usage examples
```

## Assertion Types

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact match | `{"path": "$.code", "operator": "equals", "value": 0}` |
| `exists` | Field exists | `{"path": "$.data.id", "operator": "exists"}` |
| `contains` | String contains | `{"path": "$.message", "operator": "contains", "value": "success"}` |
| `not_equals` | Not equal | `{"path": "$.status", "operator": "not_equals", "value": "error"}` |
| `greater_than` | Numeric > | `{"path": "$.count", "operator": "greater_than", "value": 0}` |
| `less_than` | Numeric < | `{"path": "$.time", "operator": "less_than", "value": 1000}` |
| `type_is` | Type check | `{"path": "$.items", "operator": "type_is", "value": "list"}` |
| `matches` | Regex match | `{"path": "$.email", "operator": "matches", "value": ".*@.*"}` |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLM_PROVIDER` | LLM provider (openai/anthropic) | `openai` |
| `LLM_API_KEY` | API key for LLM | - |
| `LLM_MODEL` | Model name | `gpt-4` |
| `API_HOST` | Server host | `0.0.0.0` |
| `API_PORT` | Server port | `8000` |

## Requirements

- Python 3.10+
- macOS (for iOS testing) or Linux/Windows (API testing only)
- Xcode (for iOS Simulator tests)

## License

MIT
