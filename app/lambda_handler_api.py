"""
Lambda handler for FastAPI application.
Uses Mangum to adapt FastAPI for AWS Lambda.
"""
from mangum import Mangum
from app.main import app

# Create Mangum handler
handler = Mangum(app, lifespan="off")

# Lambda entry point
def lambda_handler(event, context):
    """
    Lambda handler for FastAPI application.
    """
    return handler(event, context)

