import os
import boto3
from botocore.exceptions import ClientError
from app.parsers.booking import parse_email
import logfire
from app.models.booking import BookingWithMeta, FullBookingTable
from app.functions.common import store_result, get_booking_by_confirmation, normalize_booking_data
from app.functions.geocoding import geocode_address
from typing import Optional, Dict, Any
from decimal import Decimal

# Configure logfire once at module level
logfire.configure()
logfire.instrument_pydantic()

s3 = boto3.client("s3")
dynamodb = boto3.resource("dynamodb")


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

        with logfire.span("clean and validate"):
            booking_data = get_booking_by_confirmation(booking.confirmation)
            if booking_data:
                # Normalize the data to ensure all fields are present (None/empty string for missing)
                # This prevents KeyError when accessing fields that don't exist in DynamoDB
                normalized_data = normalize_booking_data(booking_data, FullBookingTable)
                # Use model_construct to allow None values for missing fields without validation errors
                booking_retrieved = FullBookingTable.model_construct(**normalized_data)
            else:
                logfire.warning("Booking not found in database", confirmation=booking.confirmation)
                continue
            
            # Check if latitude is missing, None, or empty string
            if not booking_retrieved.latitude or booking_retrieved.latitude == "":
                # Build full address, handling None values
                address_parts = []
                if booking_retrieved.street_address:
                    address_parts.append(booking_retrieved.street_address)
                if booking_retrieved.city:
                    address_parts.append(booking_retrieved.city)
                if booking_retrieved.postal_code:
                    address_parts.append(booking_retrieved.postal_code)
                
                if address_parts:
                    full_address = " ".join(address_parts)
                    logfire.info("geocoding", full_address=full_address)
                    geocode_result = geocode_address(full_address)
                    if geocode_result:
                        # Convert float values to Decimal for DynamoDB compatibility
                        latitude = geocode_result.get('latitude')
                        longitude = geocode_result.get('longitude')
                        if latitude is not None:
                            booking_retrieved.latitude = Decimal(str(latitude))
                        if longitude is not None:
                            booking_retrieved.longitude = Decimal(str(longitude))
                        logfire.info("geocode complete", 
                                   latitude=latitude, 
                                   longitude=longitude,
                                   geocode_result=geocode_result)
                    else:
                        logfire.warning("Geocoding returned no result", full_address=full_address)
                else:
                    logfire.warning(
                        "No address components available for geocoding",
                        confirmation=booking.confirmation
                    )

        with logfire.span("re-save booking"):
            store_result(
                booking_retrieved,
                os.environ.get("BOOKINGS_TABLE_NAME", "bookings"),
                {"confirmation": booking_retrieved.confirmation}
            )
    return {"statusCode": 200, "body": "OK"}




def get_booking_with_coordinates(confirmation: str, table_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Retrieve a booking by confirmation number and geocode its address.
    
    Args:
        confirmation: The booking confirmation ID
        table_name: Optional table name (defaults to BOOKINGS_TABLE_NAME env var)
        
    Returns:
        Booking dict with additional 'coordinates' field containing geocoded location,
        or None if booking not found. Coordinates will be None if geocoding fails.
    """
    booking = get_booking_by_confirmation(confirmation, table_name)
    
    if not booking:
        return None
    
    # Geocode the address if it exists
    address = booking.get("address")
    if address:
        coordinates = geocode_address(address)
        booking["coordinates"] = coordinates
    else:
        booking["coordinates"] = None
        logfire.info("No address found in booking, skipping geocoding", confirmation=confirmation)
    
    return booking


logfire.instrument_aws_lambda(lambda_handler)
