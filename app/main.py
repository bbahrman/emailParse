"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logfire

# Configure logfire
logfire.configure()
logfire.instrument_pydantic()

# Create FastAPI app
app = FastAPI(
    title="Email Parse API",
    description="API for retrieving booking details from parsed emails",
    version="1.0.0"
)

# Add CORS middleware (allow all origins for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
from app.routers import bookings
app.include_router(bookings.router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Email Parse API",
        "version": "1.0.0",
        "endpoints": {
            "get_booking_by_id": "/bookings/{confirmation}",
            "get_bookings_by_date_range": "/bookings/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

