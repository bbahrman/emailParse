import json
import os
import boto3
from botocore.exceptions import ClientError
from app.parsers.booking import parse_email
import logfire

# Configure logfire once at module level
logfire.configure()

s3 = boto3.client("s3")


def store_result(parsed: dict):
    """
    Example: write JSON to another S3 bucket/prefix.
    Swap this with DB / Obsidian export / whatever you have.
    """
    output_bucket = os.environ.get("OUTPUT_BUCKET")
    output_prefix = os.environ.get("OUTPUT_PREFIX", "parsed-emails/")
    if not output_bucket:
        # no-op if not configured
        return

    s3_key = f"{output_prefix}{parsed.get('id', 'unknown')}.json"

    s3.put_object(
        Bucket=output_bucket,
        Key=s3_key,
        Body=json.dumps(parsed).encode("utf-8"),
        ContentType="application/json",
    )


def lambda_handler(event, context):
    """
    S3 event -> download email -> parse -> store result.
    """
    logfire.info("Lambda handler invoked", event_records=len(event.get("Records", [])))
    # S3 can batch multiple records; handle them in a loop
    for record in event.get("Records", []):
        event_source = record.get("eventSource") or record.get("EventSource")
        if event_source != "aws:s3":
            # Ignore non-S3 events if any
            continue

        s3_info = record["s3"]
        bucket_name = s3_info["bucket"]["name"]
        object_key = s3_info["object"]["key"]

        # S3 keys may be URL-encoded
        from urllib.parse import unquote_plus
        object_key = unquote_plus(object_key)

        try:
            obj = s3.get_object(Bucket=bucket_name, Key=object_key)
            raw_bytes = obj["Body"].read()
            logfire.info("Fetched email from S3", bucket=bucket_name, key=object_key, size=len(raw_bytes))
        except ClientError as e:
            logfire.error("Error fetching object from S3", bucket=bucket_name, key=object_key, error=str(e))
            print(f"Error fetching object {bucket_name}/{object_key}: {e}")
            continue

        logfire.info("Parsing email", bucket=bucket_name, key=object_key)
        try:
            booking = parse_email(raw_bytes)
            
            # Convert Pydantic model to dict
            parsed = booking.model_dump(mode="json")
            
            logfire.info("Email parsed successfully", booking_id=parsed.get("id"), confirmation=parsed.get("confirmation"))

            # You might want to embed where this came from:
            parsed.setdefault("source_bucket", bucket_name)
            parsed.setdefault("source_key", object_key)

            # Ensure you have some stable identifier to use as filename / DB key
            if "id" not in parsed:
                parsed["id"] = object_key.replace("/", "_")

            store_result(parsed)
        except ValueError as e:
            # Email is not a booking (e.g., marketing email) - log and continue
            logfire.info("Skipping non-booking email", bucket=bucket_name, key=object_key, reason=str(e))
            continue
        except Exception as e:
            # Other parsing errors - log and continue
            logfire.error("Error parsing email", bucket=bucket_name, key=object_key, error=str(e))
            continue

    return {"statusCode": 200, "body": "OK"}


logfire.instrument_aws_lambda(lambda_handler)
