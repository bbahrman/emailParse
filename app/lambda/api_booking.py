import logfire
import json
from datetime import datetime
from typing import Dict, Any, Optional

logfire.configure()
logfire.instrument_pydantic()


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    Main Lambda handler for bookings API
    Handles all booking-related operations: GET, POST, PUT, DELETE
    """
    with logfire.span("lambda entry", endpoint="booking", event=event):
        # Extract request information
        http_method = event.get('httpMethod', '')
        resource = event.get('path', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        # Route to appropriate handler based on method and resource
        route_key = f"{http_method} {resource}"
        with logfire.span(
                "lambda api parsed",
                method=http_method,
                resource=resource,
                path=path_parameters,
                query_parameters=query_parameters,
                route_key=route_key
        ):
            try:
                if route_key == 'GET /booking':
                    return get_bookings(query_parameters)
                elif route_key == 'POST /booking':
                    return create_booking(event)
                elif route_key == 'PUT /bookings/{id}':
                    booking_id = path_parameters.get('id')
                    return update_booking(booking_id, event)
                elif route_key == 'DELETE /bookings/{id}':
                    booking_id = path_parameters.get('id')
                    return delete_booking(booking_id)
                else:
                    return create_response(404, {'message': f'Route not found: {route_key}'})

            except Exception as e:
                logfire.error("Error processing request:", error=e)
                return create_response(500, {'message': 'Internal Server Error'})


logfire.instrument_aws_lambda(lambda_handler)


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    response = {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',  # For CORS
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(body)
    }
    logfire.info("response", response=response)
    return response


def get_bookings(query_params: Dict[str, str]) -> Dict[str, Any]:
    with logfire.span("get_bookings", query_params=query_params):
        # Extract query parameters for filtering
        date_filter = query_params.get('date')
        status_filter = query_params.get('status')
        limit = int(query_params.get('limit', 10))

        # Mock data - in real app, this would query your database
        all_bookings = [
            {
                'id': '1',
                'customer_name': 'John Doe',
                'date': '2024-01-15',
                'time': '14:00',
                'status': 'confirmed',
                'service': 'consultation'
            },
            {
                'id': '2',
                'customer_name': 'Jane Smith',
                'date': '2024-01-16',
                'time': '10:30',
                'status': 'pending',
                'service': 'treatment'
            },
            {
                'id': '3',
                'customer_name': 'Bob Johnson',
                'date': '2024-01-15',
                'time': '16:00',
                'status': 'cancelled',
                'service': 'consultation'
            }
        ]

        # Apply filters
        filtered_bookings = all_bookings

        if date_filter:
            filtered_bookings = [b for b in filtered_bookings if b['date'] == date_filter]

        if status_filter:
            filtered_bookings = [b for b in filtered_bookings if b['status'] == status_filter]

        # Apply limit
        filtered_bookings = filtered_bookings[:limit]

        return create_response(200, {
            'bookings': filtered_bookings,
            'total': len(filtered_bookings),
            'filters_applied': {
                'date': date_filter,
                'status': status_filter,
                'limit': limit
            }
        })


def create_booking(event: Dict[str, Any]) -> Dict[str, Any]:
    with logfire.span("create_booking", event=event):
        try:
            # Parse request body
            body = json.loads(event.get('body', '{}'))

            # Validate required fields
            required_fields = ['customer_name', 'date', 'time', 'service']
            missing_fields = [field for field in required_fields if not body.get(field)]

            if missing_fields:
                return create_response(400, {
                    'message': 'Missing required fields',
                    'missing_fields': missing_fields
                })

            # Create new booking (in real app, save to database)
            new_booking = {
                'id': str(datetime.now().timestamp()),  # Simple ID generation
                'customer_name': body['customer_name'],
                'date': body['date'],
                'time': body['time'],
                'service': body['service'],
                'status': 'pending',  # Default status
                'created_at': datetime.now().isoformat()
            }

            logfire.info(f"Created booking: {new_booking['id']}")

            return create_response(201, {
                'message': 'Booking created successfully',
                'booking': new_booking
            })

        except json.JSONDecodeError:
            return create_response(400, {'message': 'Invalid JSON in request body'})


def get_booking(booking_id: str) -> Dict[str, Any]:
    with logfire.span("get_bookings", booking_id=booking_id):
        if not booking_id:
            return create_response(400, {'message': 'Booking ID is required'})

        # Mock data - in real app, query database by ID
        mock_bookings = {
            '1': {
                'id': '1',
                'customer_name': 'John Doe',
                'date': '2024-01-15',
                'time': '14:00',
                'status': 'confirmed',
                'service': 'consultation',
                'notes': 'First-time customer'
            }
        }

        booking = mock_bookings.get(booking_id)

        if not booking:
            return create_response(404, {'message': f'Booking with ID {booking_id} not found'})

        return create_response(200, {'booking': booking})


def update_booking(booking_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    with logfire.span("update_booking", booking_id=booking_id, event=event):
        if not booking_id:
            return create_response(400, {'message': 'Booking ID is required'})

        try:
            # Parse request body
            body = json.loads(event.get('body', '{}'))

            # Mock: Check if booking exists
            if booking_id not in ['1', '2', '3']:  # Simple mock check
                return create_response(404, {'message': f'Booking with ID {booking_id} not found'})

            # Update booking (in real app, update in database)
            updated_booking = {
                'id': booking_id,
                'customer_name': body.get('customer_name', 'John Doe'),
                'date': body.get('date', '2024-01-15'),
                'time': body.get('time', '14:00'),
                'service': body.get('service', 'consultation'),
                'status': body.get('status', 'confirmed'),
                'updated_at': datetime.now().isoformat()
            }

            logfire.info(f"Updated booking: {booking_id}")

            return create_response(200, {
                'message': 'Booking updated successfully',
                'booking': updated_booking
            })

        except json.JSONDecodeError:
            return create_response(400, {'message': 'Invalid JSON in request body'})


def delete_booking(booking_id: str) -> Dict[str, Any]:
    with logfire.span("delete_booking", booking_id=booking_id):
        if not booking_id:
            return create_response(400, {'message': 'Booking ID is required'})

        # Mock: Check if booking exists
        if booking_id not in ['1', '2', '3']:  # Simple mock check
            return create_response(404, {'message': f'Booking with ID {booking_id} not found'})

        # Delete booking (in real app, delete from database)
        logfire.info(f"Deleted booking: {booking_id}")

        return create_response(200, {
            'message': f'Booking {booking_id} deleted successfully'
        })
