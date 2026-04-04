"""
Lambda handler for the API Gateway HTTP API.
Uses Mangum to adapt FastAPI to AWS Lambda.
"""
from mangum import Mangum
from app.main import app

lambda_handler = Mangum(app, lifespan="off")
