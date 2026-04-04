"""
Service for querying DynamoDB bookings table.
"""
import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional, List, Dict, Any
from datetime import datetime
import logfire


class DynamoDBService:
    """Service for interacting with DynamoDB bookings table."""
    
    def __init__(self):
        self.table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(self.table_name)
    
    def get_booking_by_id(self, confirmation: str) -> Optional[Dict[str, Any]]:
        """
        Get a single booking by confirmation ID.
        
        Args:
            confirmation: The booking confirmation ID
            
        Returns:
            Booking item as dict, or None if not found
        """
        try:
            with logfire.span("dynamodb_get_item", confirmation=confirmation):
                response = self.table.get_item(
                    Key={"confirmation": confirmation}
                )
                
                if "Item" in response:
                    return self._convert_dynamodb_item(response["Item"])
                return None
                
        except ClientError as e:
            logfire.error("Error getting booking from DynamoDB", 
                         error=str(e),
                         confirmation=confirmation)
            raise
    
    def get_bookings_by_date_range(
        self, 
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_field: str = "check_in_date"
    ) -> List[Dict[str, Any]]:
        """
        Get bookings within a date range by scanning the table.
        
        Note: This uses a scan operation which can be slow for large tables.
        For better performance, consider adding a GSI on the date field.
        
        Args:
            start_date: Start date (ISO format string, e.g., "2025-11-17")
            end_date: End date (ISO format string, e.g., "2025-11-20")
            date_field: Field to filter on (default: "check_in_date")
            
        Returns:
            List of booking items
        """
        try:
            with logfire.span("dynamodb_scan_date_range", 
                             start_date=start_date,
                             end_date=end_date,
                             date_field=date_field):
                # Build filter expression
                filter_expressions = []
                expression_attribute_names = {}
                expression_attribute_values = {}
                
                if start_date:
                    filter_expressions.append(f"#{date_field} >= :start_date")
                    expression_attribute_names[f"#{date_field}"] = date_field
                    expression_attribute_values[":start_date"] = start_date
                
                if end_date:
                    filter_expressions.append(f"#{date_field} <= :end_date")
                    expression_attribute_names[f"#{date_field}"] = date_field
                    expression_attribute_values[":end_date"] = end_date
                
                # Scan parameters
                scan_kwargs = {}
                if filter_expressions:
                    scan_kwargs["FilterExpression"] = " AND ".join(filter_expressions)
                    scan_kwargs["ExpressionAttributeNames"] = expression_attribute_names
                    scan_kwargs["ExpressionAttributeValues"] = expression_attribute_values
                
                # Perform scan (with pagination)
                all_items = []
                response = self.table.scan(**scan_kwargs)
                all_items.extend(response.get("Items", []))
                
                # Handle pagination
                while "LastEvaluatedKey" in response:
                    scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                    response = self.table.scan(**scan_kwargs)
                    all_items.extend(response.get("Items", []))
                
                # Convert DynamoDB items to regular dicts
                return [self._convert_dynamodb_item(item) for item in all_items]
                
        except ClientError as e:
            logfire.error("Error scanning bookings from DynamoDB", 
                         error=str(e),
                         start_date=start_date,
                         end_date=end_date)
            raise
    
    def get_all_cities(self) -> List[Dict[str, Any]]:
        """
        Get all city items from DynamoDB.
        Cities are identified by having a city_id field.
        """
        try:
            with logfire.span("dynamodb_scan_cities"):
                scan_kwargs = {
                    "FilterExpression": "attribute_exists(city_id)",
                }
                all_items = []
                response = self.table.scan(**scan_kwargs)
                all_items.extend(response.get("Items", []))

                while "LastEvaluatedKey" in response:
                    scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                    response = self.table.scan(**scan_kwargs)
                    all_items.extend(response.get("Items", []))

                return [self._convert_dynamodb_item(item) for item in all_items]

        except ClientError as e:
            logfire.error("Error scanning cities from DynamoDB", error=str(e))
            raise

    def get_all_bookings(self) -> List[Dict[str, Any]]:
        """
        Get all booking items from DynamoDB.
        Bookings are identified by having a guest_name field (not city_id).
        """
        try:
            with logfire.span("dynamodb_scan_bookings"):
                scan_kwargs = {
                    "FilterExpression": "attribute_exists(guest_name) AND attribute_not_exists(city_id)",
                }
                all_items = []
                response = self.table.scan(**scan_kwargs)
                all_items.extend(response.get("Items", []))

                while "LastEvaluatedKey" in response:
                    scan_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]
                    response = self.table.scan(**scan_kwargs)
                    all_items.extend(response.get("Items", []))

                return [self._convert_dynamodb_item(item) for item in all_items]

        except ClientError as e:
            logfire.error("Error scanning bookings from DynamoDB", error=str(e))
            raise

    def get_cities_by_trip(self, trip_name: str) -> List[Dict[str, Any]]:
        """Get all cities that have a visit with the given trip name."""
        cities = self.get_all_cities()
        return [
            city for city in cities
            if any(
                visit.get("trip") == trip_name
                for visit in (city.get("visits") or [])
            )
        ]

    def get_all_trip_names(self) -> List[str]:
        """Get all unique trip names across all cities."""
        cities = self.get_all_cities()
        trip_names = set()
        for city in cities:
            for visit in (city.get("visits") or []):
                if visit.get("trip"):
                    trip_names.add(visit["trip"])
        return sorted(trip_names)

    def _convert_dynamodb_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert DynamoDB item format to regular Python dict.
        
        boto3 resource API returns native Python types, but we handle both formats
        in case we switch to low-level client API.
        """
        converted = {}
        for key, value in item.items():
            if isinstance(value, dict):
                # DynamoDB type descriptor (low-level API format)
                if "S" in value:
                    converted[key] = value["S"]
                elif "N" in value:
                    # Try to convert to int, fallback to float
                    num_str = value["N"]
                    try:
                        if "." in num_str:
                            converted[key] = float(num_str)
                        else:
                            converted[key] = int(num_str)
                    except ValueError:
                        converted[key] = num_str
                elif "BOOL" in value:
                    converted[key] = value["BOOL"]
                elif "NULL" in value:
                    converted[key] = None
                else:
                    converted[key] = value
            else:
                # Already native Python type (boto3 resource API)
                converted[key] = value
        return converted

