import json
import os
import boto3
from botocore.exceptions import ClientError
from app.parsers.booking import parse_email
import logfire
from datetime import datetime

# Configure logfire once at module level
logfire.configure()
logfire.instrument_pydantic()

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def store_result(parsed: dict):
    """
    Store booking in DynamoDB bookings table.
    Uses 'confirmation' as the primary key.
    """
    table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
    table = dynamodb.Table(table_name)
    
    # Ensure confirmation exists (required for primary key)
    confirmation = parsed.get("confirmation")
    if not confirmation:
        confirmation = parsed.get("id") or parsed.get("source_key", "unknown").replace("/", "_")
        parsed["confirmation"] = confirmation
    
    # Convert HttpUrl to string if present
    website = str(parsed.get("website", "")) if parsed.get("website") else None
    
    # Prepare DynamoDB item (upsert)
    now = datetime.utcnow().isoformat()
    
    # Use UpdateItem with SET for updated_at and SET if_not_exists for created_at
    # This ensures created_at is only set on first insert
    try:
        logfire.info("Attempting to store booking in DynamoDB", 
                    confirmation=confirmation,
                    table_name=table_name,
                    booking_name=parsed.get("name"))
        
        with logfire.span("dynamodb_update_item", table=table_name, confirmation=confirmation):
            response = table.update_item(
                Key={"confirmation": confirmation},
                UpdateExpression="""
                    SET #name = :name,
                        #address = :address,
                        check_in_date = :check_in_date,
                        check_out_date = :check_out_date,
                        check_in_time = :check_in_time,
                        check_out_time = :check_out_time,
                        early_check_in_time = :early_check_in_time,
                        early_check_in_cost = :early_check_in_cost,
                        breakfast_included = :breakfast_included,
                        cancellation_terms = :cancellation_terms,
                        city = :city,
                        booking_date = :booking_date,
                        what3words = :what3words,
                        website = :website,
                        amount_paid = :amount_paid,
                        amount_total = :amount_total,
                        room_type = :room_type,
                        source_bucket = :source_bucket,
                        source_key = :source_key,
                        updated_at = :updated_at,
                        created_at = if_not_exists(created_at, :created_at)
                """,
                ExpressionAttributeNames={
                    "#name": "name",
                    "#address": "address"
                },
                ExpressionAttributeValues={
                    ":name": parsed.get("name"),
                    ":check_in_date": parsed.get("check_in_date"),
                    ":check_out_date": parsed.get("check_out_date"),
                    ":check_in_time": parsed.get("check_in_time"),
                    ":check_out_time": parsed.get("check_out_time"),
                    ":early_check_in_time": parsed.get("early_check_in_time"),
                    ":early_check_in_cost": parsed.get("early_check_in_cost"),
                    ":breakfast_included": parsed.get("breakfast_included", False),
                    ":cancellation_terms": parsed.get("cancellation_terms"),
                    ":address": parsed.get("address"),
                    ":city": parsed.get("city"),
                    ":booking_date": parsed.get("booking_date"),
                    ":what3words": parsed.get("what3words"),
                    ":website": website,
                    ":amount_paid": parsed.get("amount_paid"),
                    ":amount_total": parsed.get("amount_total"),
                    ":room_type": parsed.get("room_type"),
                    ":source_bucket": parsed.get("source_bucket"),
                    ":source_key": parsed.get("source_key"),
                    ":updated_at": now,
                    ":created_at": now
                },
                ReturnValues="ALL_NEW"  # Return the updated item for verification
            )
            
            logfire.info("DynamoDB update_item response", 
                        confirmation=confirmation,
                        response_metadata=response.get("ResponseMetadata", {}).get("HTTPStatusCode"),
                        item=response.get("Attributes", {}))
        
        logfire.info("Booking successfully stored in DynamoDB", 
                    confirmation=confirmation,
                    booking_name=parsed.get("name"),
                    table_name=table_name)
        print(f"✓ Stored booking in DynamoDB: {confirmation}", flush=True)
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logfire.error("DynamoDB ClientError storing booking", 
                     error_code=error_code,
                     error_message=error_message,
                     confirmation=confirmation,
                     table_name=table_name)
        print(f"✗ DynamoDB error: {error_code} - {error_message}", flush=True)
        raise
    except Exception as e:
        logfire.error("Unexpected error storing booking in DynamoDB", 
                     error=str(e),
                     error_type=type(e).__name__,
                     confirmation=confirmation,
                     table_name=table_name)
        print(f"✗ Error storing booking: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise


def lambda_handler(event, context):
    """
    S3 event -> download email -> parse -> store result.
    """
    print(f"Lambda handler invoked - Records: {len(event.get('Records', []))}", flush=True)
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

        with logfire.span("process_email", bucket=bucket_name, key=object_key):
            try:
                obj = s3.get_object(Bucket=bucket_name, Key=object_key)
                raw_bytes = obj["Body"].read()
                logfire.info("Fetched email from S3", bucket=bucket_name, key=object_key, size=len(raw_bytes))
            except ClientError as e:
                logfire.error("Error fetching object from S3", bucket=bucket_name, key=object_key, error=str(e))
                print(f"Error fetching object {bucket_name}/{object_key}: {e}")
                continue

            with logfire.span("parse_email", bucket=bucket_name, key=object_key):
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

                except ValueError as e:
                    # Email is not a booking (e.g., marketing email) - log and continue
                    logfire.info("Skipping non-booking email", bucket=bucket_name, key=object_key, reason=str(e))
                    continue
                except Exception as e:
                    # Other parsing errors - log and continue
                    logfire.error("Error parsing email", bucket=bucket_name, key=object_key, error=str(e))
                    continue

            with logfire.span("store_result", booking_id=parsed.get("id")):
                store_result(parsed)

    return {"statusCode": 200, "body": "OK"}


logfire.instrument_aws_lambda(lambda_handler)
