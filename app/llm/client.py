from openai import OpenAI
import os
import boto3
import json
from botocore.exceptions import ClientError

def get_openai_api_key():
    """Get OpenAI API key from environment variable or Secrets Manager."""
    # First try environment variable (for local development)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key
    
    # If not found, try to fetch from Secrets Manager
    secret_arn = os.getenv("OPENAI_API_KEY_SECRET_ARN")
    if secret_arn:
        try:
            secrets_client = boto3.client('secretsmanager')
            response = secrets_client.get_secret_value(SecretId=secret_arn)
            secret = json.loads(response['SecretString'])
            return secret.get('api_key')
        except (ClientError, json.JSONDecodeError, KeyError) as e:
            print(f"Error fetching secret from Secrets Manager: {e}")
            return None
    
    return None

client = OpenAI(api_key=get_openai_api_key())
