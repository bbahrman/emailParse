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
    try:
        with logfire.span("dynamodb_update_item", table=table_name, confirmation=parsed.confirmation):
            response = update_table(parsed, {"confirmation": parsed.confirmation}, os.environ.get("BOOKINGS_TABLE_NAME", "bookings"))

            logfire.info(
                "DynamoDB update_item response",
                confirmation=parsed.confirmation,
                response_metadata=response.get("ResponseMetadata", {}).get("HTTPStatusCode"),
                item=response.get("Attributes", {}),
                provider_name=parsed.provider_name,
                table_name=table_name
            )
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))
        logfire.error("DynamoDB ClientError storing booking", 
                     error_code=error_code,
                     error_message=error_message,
                     confirmation=parsed.confirmation,
                     table_name=table_name)
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


def update_table(
        model,
        key_object,
        table_name
):
    values_dict = model.model_dump(exclude_unset=True)
    table = dynamodb.Table(table_name)
    # Prepare DynamoDB item (upsert)
    now = datetime.utcnow().isoformat()

    update_parts = []
    expression_attribute_names = {}
    expression_attribute_values = {}

    # Always update these fields
    update_parts.append("updated_at = :updated_at")
    update_parts.append("created_at = if_not_exists(created_at, :created_at)")
    expression_attribute_values[":updated_at"] = now
    expression_attribute_values[":created_at"] = now

    # Dynamically process all fields from the model
    for field_name, field_value in values_dict.items():
        if field_name == "website":
            field_value = str(field_value)

        if field_name in key_object:
            continue

        update_parts.append(f"{field_name} = :{field_name}")
        expression_attribute_values[f":{field_name}"] = field_value

    # Build the update expression
    update_expression = "SET " + ", ".join(update_parts)

    response = table.update_item(
        Key=key_object,
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ReturnValues="ALL_NEW"  # Return the updated item for verification
    )

    return response


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
