import os
import boto3
from botocore.exceptions import ClientError
from app.parsers.booking import parse_email
import logfire
from app.models.booking import BookingWithMeta
from app.functions.common import store_result

# Configure logfire once at module level
logfire.configure()
logfire.instrument_pydantic()

s3 = boto3.client("s3")


def lambda_handler(event, context):
    logfire.info(
        "Lambda handler invoked",
        endpoint="s3_parse_email",
        event=event,
        event_records=len(event.get("Records", []))
    )

    # S3 can batch multiple records; handle them in a loop
    for record in event.get("Records", []):
        event_source = record.get("eventSource") or record.get("EventSource")
        if event_source != "aws:s3":
            # Ignore non-S3 events if any
            continue

        s3_info = record["s3"]
        bucket_name = s3_info["bucket"]["name"]
        object_key = s3_info["object"]["key"]

        with logfire.span("process_email", bucket=bucket_name, key=object_key):
            try:
                obj = s3.get_object(Bucket=bucket_name, Key=object_key)
                raw_bytes = obj["Body"].read()
                logfire.info("Fetched email from S3", bucket=bucket_name, key=object_key, size=len(raw_bytes))
            except ClientError as e:
                logfire.error("Error fetching object from S3", bucket=bucket_name, key=object_key, error=str(e))
                continue

            try:
                # call openAI to parse email
                base_booking = parse_email(raw_bytes)
                booking = BookingWithMeta(
                    **base_booking.model_dump(),
                    source_key=object_key,
                )
                logfire.info("Email parsed successfully", confirmation=booking.confirmation)
            except ValueError as e:
                # Email is not a booking (e.g., marketing email) - log and continue
                logfire.info("Skipping non-booking email", bucket=bucket_name, key=object_key, reason=str(e))
                continue
            except Exception as e:
                # Other parsing errors - log and continue
                logfire.error("Error parsing email", bucket=bucket_name, key=object_key, error=str(e))
                continue

        store_result(
            booking,
            os.environ.get("BOOKINGS_TABLE_NAME", "bookings"),
            {"confirmation": booking.confirmation}
        )

    return {"statusCode": 200, "body": "OK"}


logfire.instrument_aws_lambda(lambda_handler)
