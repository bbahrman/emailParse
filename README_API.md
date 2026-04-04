# Email Parse API

FastAPI application for retrieving booking details from DynamoDB.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables (optional, defaults shown):
```bash
export BOOKINGS_TABLE_NAME=bookings  # Default DynamoDB table name
export AWS_REGION=us-east-1          # AWS region
```

3. Ensure AWS credentials are configured (via `~/.aws/credentials` or environment variables).

## Running the API

### Development (with auto-reload):
```bash
python run_api.py
```

Or using uvicorn directly:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## API Endpoints

### Get Booking by ID
```
GET /bookings/{confirmation}
```

Example:
```bash
curl http://localhost:8000/bookings/RL37906759
```

### Get Bookings by Date Range
```
GET /bookings/?start_date=2025-11-17&end_date=2025-11-20&date_field=check_in_date
```

Query Parameters:
- `start_date` (optional): Start date for filtering (ISO format: YYYY-MM-DD or full date string)
- `end_date` (optional): End date for filtering (ISO format: YYYY-MM-DD or full date string)
- `date_field` (optional, default: "check_in_date"): Field to filter on
  - Options: `check_in_date`, `check_out_date`, `booking_date`, `created_at`

Examples:
```bash
# Get all bookings with check-in between Nov 17-20, 2025
curl "http://localhost:8000/bookings/?start_date=2025-11-17&end_date=2025-11-20"

# Get all bookings created today
curl "http://localhost:8000/bookings/?start_date=2025-11-17&date_field=created_at"

# Get all bookings (no filters)
curl "http://localhost:8000/bookings/"
```

### Health Check
```
GET /health
```

### Root
```
GET /
```

## Response Format

### Single Booking
```json
{
  "confirmation": "RL37906759",
  "name": "Benjamin",
  "check_in_date": "17 December 2025",
  "check_out_date": "20 December 2025",
  ...
}
```

### List of Bookings
```json
{
  "bookings": [
    {
      "confirmation": "RL37906759",
      "name": "Benjamin",
      ...
    }
  ],
  "count": 1
}
```

## Performance Notes

- **Get by ID**: Fast O(1) lookup using DynamoDB GetItem
- **Date Range Query**: Uses DynamoDB Scan with filter, which can be slow for large tables
  - For better performance, consider adding a Global Secondary Index (GSI) on the date field
  - Current implementation handles pagination automatically

## Error Handling

- `404 Not Found`: Booking with the specified confirmation ID not found
- `500 Internal Server Error`: DynamoDB errors or other server issues

