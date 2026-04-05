import anthropic
import os
import boto3
import json
from botocore.exceptions import ClientError


def get_anthropic_api_key():
    """Get Anthropic API key from environment variable or Secrets Manager."""
    api_key = os.getenv("TRAVEL_ANTHROPIC_API_KEY")
    if api_key:
        return api_key

    secret_arn = os.getenv("TRAVEL_ANTHROPIC_API_KEY_SECRET_ARN")
    if secret_arn:
        try:
            secrets_client = boto3.client("secretsmanager")
            response = secrets_client.get_secret_value(SecretId=secret_arn)
            secret = json.loads(response["SecretString"])
            return secret.get("api_key")
        except (ClientError, json.JSONDecodeError, KeyError) as e:
            print(f"Error fetching secret from Secrets Manager: {e}")
            return None

    return None


client = anthropic.Anthropic(api_key=get_anthropic_api_key())
