# Backend - JiuWei CRM

FastAPI backend for the JiuWei CRM system.

## Tech Stack

- Python 3.13
- FastAPI
- SQLAlchemy
- Pydantic
- python-jose (JWT)

## Getting Started

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /api/v1/health` - Health check

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

- `DATABASE_URL` - Database connection string
- `JWT_SECRET_KEY` - Secret key for JWT tokens
- `UPLOAD_DIR` - Upload directory path
- `TEMP_FILE_RETENTION_DAYS` - Days to retain temporary files
- `CORS_ORIGINS` - Comma-separated list of allowed CORS origins
