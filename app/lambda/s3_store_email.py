import os
import boto3
from botocore.exceptions import ClientError
from app.parsers.booking import parse_email
import logfire
from datetime import datetime
from app.models.booking import BookingWithMeta

# Configure logfire once at module level
logfire.configure()
logfire.instrument_pydantic()

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


def store_result(parsed: BookingWithMeta):
    table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
    table = dynamodb.Table(table_name)
    
    # Convert HttpUrl to string if present
    website = str(parsed.website) if parsed.website else None
    
    # Prepare DynamoDB item (upsert)
    now = datetime.utcnow().isoformat()
    
    # Use UpdateItem with SET for updated_at and SET if_not_exists for created_at
    # This ensures created_at is only set on first insert
    try:
        logfire.info(
            "Attempting to store booking in DynamoDB",
            confirmation=parsed.confirmation,
            table_name=table_name,
            provider_name=parsed.provider_name
        )
        
        with logfire.span("dynamodb_update_item", table=table_name, confirmation=parsed.confirmation):
            response = table.update_item(
                Key={"confirmation": parsed.confirmation},
                UpdateExpression="""
                    SET guest_name = :guest_name,
                        provider_name = :provider_name,
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
                        source_key = :source_key,
                        updated_at = :updated_at,
                        created_at = if_not_exists(created_at, :created_at)
                """,
                ExpressionAttributeNames={
                    "#address": "address"
                },
                ExpressionAttributeValues={
                    ":guest_name": parsed.guest_name,
                    ":provider_name": parsed.provider_name,
                    ":check_in_date": parsed.check_in_date,
                    ":check_out_date": parsed.check_out_date,
                    ":check_in_time": parsed.check_in_time,
                    ":check_out_time": parsed.check_out_time,
                    ":early_check_in_time": parsed.early_check_in_time,
                    ":early_check_in_cost": parsed.early_check_in_cost,
                    ":breakfast_included": parsed.breakfast_included,
                    ":cancellation_terms": parsed.cancellation_terms,
                    ":address": parsed.address,
                    ":city": parsed.city,
                    ":booking_date": parsed.booking_date,
                    ":what3words": parsed.what3words,
                    ":website": website,
                    ":amount_paid": parsed.amount_paid,
                    ":amount_total": parsed.amount_total,
                    ":room_type": parsed.room_type,
                    ":source_key": parsed.source_key,
                    ":updated_at": now,
                    ":created_at": now
                },
                ReturnValues="ALL_NEW"  # Return the updated item for verification
            )
            
            logfire.info("DynamoDB update_item response", 
                        confirmation=parsed.confirmation,
                        response_metadata=response.get("ResponseMetadata", {}).get("HTTPStatusCode"),
                        item=response.get("Attributes", {}))
        
        logfire.info("Booking successfully stored in DynamoDB", 
                    confirmation=parsed.confirmation,
                    provider_name=parsed.provider_name,
                    table_name=table_name)
        print(f"✓ Stored booking in DynamoDB: {parsed.confirmation}", flush=True)
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logfire.error("DynamoDB ClientError storing booking", 
                     error_code=error_code,
                     error_message=error_message,
                     confirmation=parsed.confirmation,
                     table_name=table_name)
        print(f"✗ DynamoDB error: {error_code} - {error_message}", flush=True)
        raise
    except Exception as e:
        logfire.error("Unexpected error storing booking in DynamoDB", 
                     error=str(e),
                     error_type=type(e).__name__,
                     confirmation=parsed.confirmation,
                     table_name=table_name)
        print(f"✗ Error storing booking: {e}", flush=True)
        import traceback
        print(traceback.format_exc(), flush=True)
        raise


def lambda_handler(event, context):
    with logfire.span("lambda entry", endpoint="s3_parse_email", event=event):
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

            with logfire.span("process_email", bucket=bucket_name, key=object_key):
                try:
                    obj = s3.get_object(Bucket=bucket_name, Key=object_key)
                    raw_bytes = obj["Body"].read()
                    logfire.info("Fetched email from S3", bucket=bucket_name, key=object_key, size=len(raw_bytes))
                except ClientError as e:
                    logfire.error("Error fetching object from S3", bucket=bucket_name, key=object_key, error=str(e))
                    continue

                with logfire.span("parse_email", bucket=bucket_name, key=object_key):
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

                with logfire.span("store_result"):
                    store_result(booking)

        return {"statusCode": 200, "body": "OK"}


logfire.instrument_aws_lambda(lambda_handler)
