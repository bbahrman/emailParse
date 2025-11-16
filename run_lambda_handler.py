#!/usr/bin/env python3
"""
Run lambda_handler directly with a test S3 event payload.
This script mocks S3 to serve the local fixture file and calls lambda_handler.
"""
import pathlib
import sys
from unittest.mock import Mock, MagicMock, patch
from botocore.exceptions import ClientError

# Add project root to path
PROJECT_ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.app import lambda_handler

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures"


def load_email_bytes(name: str) -> bytes:
    """Load raw email content as bytes from fixtures."""
    path = FIXTURE_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"Fixture not found: {path}")
    return path.read_bytes()


def create_s3_event(bucket_name: str, object_key: str) -> dict:
    """Create a mock AWS Lambda S3 event structure."""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-east-1",
                "eventTime": "2025-03-20T11:22:42.000Z",
                "eventName": "ObjectCreated:Put",
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "testConfigRule",
                    "bucket": {
                        "name": bucket_name,
                        "ownerIdentity": {"principalId": "EXAMPLE"},
                        "arn": f"arn:aws:s3:::{bucket_name}",
                    },
                    "object": {
                        "key": object_key,
                        "size": 1024,
                        "eTag": "0123456789abcdef0123456789abcdef",
                        "sequencer": "0A1B2C3D4E5F678901",
                    },
                },
            }
        ]
    }


def main():
    """Run lambda_handler with mocked S3."""
    # Load the fixture email file
    email_bytes = load_email_bytes("hub_premier_inn_test.eml")
    print(f"Loaded email fixture: {len(email_bytes)} bytes")
    
    # Create S3 event
    bucket_name = "test-email-bucket"
    object_key = "emails/hub_premier_inn_test.eml"
    event = create_s3_event(bucket_name, object_key)
    
    # Mock Lambda context
    context = Mock()
    context.function_name = "test-lambda"
    context.aws_request_id = "test-request-id"
    
    # Mock S3 client to return our fixture file
    with patch("app.app.s3") as mock_s3_client:
        mock_s3_response = {
            "Body": MagicMock(read=Mock(return_value=email_bytes))
        }
        mock_s3_client.get_object.return_value = mock_s3_response
        
        print(f"\n{'='*60}")
        print("Running lambda_handler with test S3 event")
        print(f"{'='*60}")
        print(f"Bucket: {bucket_name}")
        print(f"Key: {object_key}")
        print(f"Event records: {len(event['Records'])}")
        print(f"{'='*60}\n")
        
        try:
            # Call lambda_handler
            result = lambda_handler(event, context)
            
            print(f"\n{'='*60}")
            print("Lambda handler completed successfully!")
            print(f"Result: {result}")
            print(f"{'='*60}\n")
            
            # Verify S3 was called
            mock_s3_client.get_object.assert_called_once_with(
                Bucket=bucket_name,
                Key=object_key
            )
            print("✓ S3 get_object was called correctly")
            
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"ERROR: Lambda handler failed: {e}")
            print(f"{'='*60}\n")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()

