"""
FastAPI application for travel booking and trip management.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import bookings, cities, trips, export
import logfire

logfire.configure()
logfire.instrument_pydantic()

app = FastAPI(
    title="Travel Booking API",
    description="API for managing travel bookings, cities, trips, and Obsidian integration",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logfire.instrument_fastapi(app)

app.include_router(bookings.router)
app.include_router(cities.router)
app.include_router(trips.router)
app.include_router(export.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
