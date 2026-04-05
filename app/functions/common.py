import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import logfire
from typing import Optional, Dict, Any, Type

dynamodb = boto3.resource("dynamodb")


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
    # Use expression attribute names (#alias) for all fields to avoid DynamoDB reserved keyword conflicts
    for field_name, field_value in values_dict.items():
        if field_name == "website":
            field_value = str(field_value)

        if field_name in key_object or field_value == "":
            continue

        alias = f"#f_{field_name}"
        update_parts.append(f"{alias} = :{field_name}")
        expression_attribute_names[alias] = field_name
        expression_attribute_values[f":{field_name}"] = field_value

    # Build the update expression
    update_expression = "SET " + ", ".join(update_parts)

    update_kwargs = {
        "Key": key_object,
        "UpdateExpression": update_expression,
        "ExpressionAttributeValues": expression_attribute_values,
        "ReturnValues": "ALL_NEW",
    }
    if expression_attribute_names:
        update_kwargs["ExpressionAttributeNames"] = expression_attribute_names

    response = table.update_item(**update_kwargs)

    return response

def store_result(parsed, table_name, key):
    with logfire.span("store_result", key=key, table_name=table_name, object=parsed):
        try:
            response = update_table(parsed, key, table_name)

            logfire.info(
                "DynamoDB update_item response",
                response_metadata=response.get("ResponseMetadata", {}).get("HTTPStatusCode"),
                item=response.get("Attributes", {}),
                table_name=table_name
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logfire.error(
                "DynamoDB ClientError",
                error_code=error_code,
                error_message=error_message,
                table_name=table_name
            )
            raise
        except Exception as e:
            logfire.error(
                "Unexpected error storing in DynamoDB",
                error=str(e),
                error_type=type(e).__name__,
                table_name=table_name)
            import traceback
            print(traceback.format_exc(), flush=True)
            raise


def get_booking_by_confirmation(confirmation: str) -> Optional[Dict[str, Any]]:
    with logfire.span("get_booking_by_confirmation", confirmation=confirmation):
        try:
            table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
            table = dynamodb.Table(table_name)
            response = table.get_item(
                Key={"confirmation": confirmation}
            )

            if "Item" in response:
                booking = response["Item"]
                logfire.info(
                    "Retrieved booking from DynamoDB",
                    confirmation=confirmation,
                    has_address="street_address" in booking and booking.get("street_address")
                )
                return booking
            else:
                logfire.info("Booking not found", confirmation=confirmation)
                return None

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logfire.error("Error retrieving booking from DynamoDB",
                          error_code=error_code,
                          error_message=error_message,
                          confirmation=confirmation,
                          table_name=table_name)
            raise


def normalize_booking_data(booking_data: Optional[Dict[str, Any]], model_class) -> Dict[str, Any]:
    """
    Normalize booking data from DynamoDB by ensuring all model fields are present.
    Missing fields will be populated with None to prevent KeyError when accessing fields.
    
    Note: This allows None values for all missing fields. Use model_construct() instead of
    model_validate() when constructing the model to allow None values for required fields.
    
    Args:
        booking_data: Raw booking data from DynamoDB (or None)
        model_class: The Pydantic model class to normalize against
        
    Returns:
        Dict with all model fields present (None for missing fields)
    """
    if booking_data is None:
        booking_data = {}
    
    # Get all field names from the model
    model_fields = set(model_class.model_fields.keys())
    
    # Get all keys present in the data
    data_keys = set(booking_data.keys())
    
    # Create normalized dict with all model fields
    normalized = booking_data.copy()
    
    # Add None for any missing fields to prevent KeyError when accessing
    missing_fields = model_fields - data_keys
    for field_name in missing_fields:
        normalized[field_name] = None
    
    return normalized
