# tests/test_lambda_handler.py
import pathlib
from unittest.mock import Mock, patch, MagicMock
import pytest
from app.app import lambda_handler

FIXTURE_DIR = pathlib.Path(__file__).parent / "fixtures"


def load_email_bytes(name: str) -> bytes:
    """Helper to load raw email content as bytes from fixtures."""
    path = FIXTURE_DIR / name
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


@patch("app.app.s3")
@patch("app.app.store_result")
@pytest.mark.integration
def test_lambda_handler_s3_event(mock_store_result, mock_s3_client):
    """Test lambda_handler processes S3 event and parses email."""
    # Load the fixture email file
    email_bytes = load_email_bytes("hub_premier_inn_test.eml")
    
    # Mock S3 get_object response
    mock_s3_response = {
        "Body": MagicMock(read=Mock(return_value=email_bytes))
    }
    mock_s3_client.get_object.return_value = mock_s3_response
    
    # Create S3 event
    bucket_name = "test-email-bucket"
    object_key = "emails/hub_premier_inn_test.eml"
    event = create_s3_event(bucket_name, object_key)
    
    # Mock context (Lambda context object)
    context = Mock()
    
    # Call lambda_handler
    result = lambda_handler(event, context)
    
    # Verify S3 get_object was called with correct parameters
    mock_s3_client.get_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=object_key
    )
    
    # Verify store_result was called
    assert mock_store_result.called
    
    # Get the parsed result that was passed to store_result
    call_args = mock_store_result.call_args[0][0]
    
    # Verify the parsed result has expected fields
    assert "source_bucket" in call_args
    assert call_args["source_bucket"] == bucket_name
    assert "source_key" in call_args
    assert call_args["source_key"] == object_key
    assert "id" in call_args
    
    # Verify return value
    assert result == {"statusCode": 200, "body": "OK"}


@patch("app.app.s3")
@patch("app.app.store_result")
def test_lambda_handler_url_encoded_key(mock_store_result, mock_s3_client):
    """Test lambda_handler handles URL-encoded S3 object keys."""
    email_bytes = load_email_bytes("hub_premier_inn_test.eml")
    
    mock_s3_response = {
        "Body": MagicMock(read=Mock(return_value=email_bytes))
    }
    mock_s3_client.get_object.return_value = mock_s3_response
    
    bucket_name = "test-email-bucket"
    # URL-encoded key (spaces become + or %20)
    object_key_encoded = "emails/test%20email.eml"
    object_key_decoded = "emails/test email.eml"
    
    event = create_s3_event(bucket_name, object_key_encoded)
    context = Mock()
    
    result = lambda_handler(event, context)
    
    # Verify get_object was called with decoded key
    mock_s3_client.get_object.assert_called_once_with(
        Bucket=bucket_name,
        Key=object_key_decoded
    )
    
    assert result == {"statusCode": 200, "body": "OK"}


@patch("app.app.s3")
@patch("app.app.store_result")
def test_lambda_handler_s3_error(mock_store_result, mock_s3_client):
    """Test lambda_handler handles S3 errors gracefully."""
    from botocore.exceptions import ClientError
    
    # Mock S3 get_object to raise ClientError
    mock_s3_client.get_object.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
        "GetObject"
    )
    
    bucket_name = "test-email-bucket"
    object_key = "emails/nonexistent.eml"
    event = create_s3_event(bucket_name, object_key)
    context = Mock()
    
    # Should not raise, but continue to next record
    result = lambda_handler(event, context)
    
    # store_result should not be called if S3 fetch failed
    assert not mock_store_result.called
    
    # Should still return success (error was logged, not fatal)
    assert result == {"statusCode": 200, "body": "OK"}


@patch("app.app.s3")
@patch("app.app.store_result")
def test_lambda_handler_non_s3_event(mock_store_result, mock_s3_client):
    """Test lambda_handler ignores non-S3 events."""
    event = {
        "Records": [
            {
                "eventSource": "aws:sqs",
                "body": "some message"
            }
        ]
    }
    context = Mock()
    
    result = lambda_handler(event, context)
    
    # S3 client should not be called
    assert not mock_s3_client.get_object.called
    # store_result should not be called
    assert not mock_store_result.called
    
    assert result == {"statusCode": 200, "body": "OK"}


@patch("app.app.s3")
@patch("app.app.store_result")
def test_lambda_handler_multiple_records(mock_store_result, mock_s3_client):
    """Test lambda_handler processes multiple S3 records."""
    email_bytes = load_email_bytes("hub_premier_inn_test.eml")
    
    mock_s3_response = {
        "Body": MagicMock(read=Mock(return_value=email_bytes))
    }
    mock_s3_client.get_object.return_value = mock_s3_response
    
    # Create event with multiple records
    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "bucket1"},
                    "object": {"key": "email1.eml"}
                }
            },
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "bucket2"},
                    "object": {"key": "email2.eml"}
                }
            },
            {
                "eventSource": "aws:sqs",  # This should be ignored
                "body": "some message"
            }
        ]
    }
    context = Mock()
    
    result = lambda_handler(event, context)
    
    # Should process 2 S3 records
    assert mock_s3_client.get_object.call_count == 2
    # store_result should be called twice
    assert mock_store_result.call_count == 2
    
    assert result == {"statusCode": 200, "body": "OK"}

