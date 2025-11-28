import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import logfire

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
    for field_name, field_value in values_dict.items():
        if field_name == "website":
            field_value = str(field_value)

        if field_name in key_object or field_value == "":
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