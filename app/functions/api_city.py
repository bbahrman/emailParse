import os
import logfire
import json
from typing import Dict, Any, Optional, List
from decimal import Decimal
from pydantic import BaseModel
from app.models.booking import City, Visit
from app.functions.common import store_result, get_booking_by_confirmation, normalize_booking_data
from app.functions.geocoding import geocode_address

logfire.configure()
logfire.instrument_pydantic()


# Helper class for storing cities in DynamoDB (visits as dict list)
class CityForStorage(BaseModel):
    city_id: str
    city_name: str
    country: str
    state: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    location_name: Optional[str] = None
    visits: Optional[List[Dict[str, Any]]] = []


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    with logfire.span("lambda entry", endpoint="city", event=event):
        # Extract request information - handle both REST API and HTTP API formats
        http_method = event.get('httpMethod') or event.get('requestContext', {}).get('http', {}).get('method', '')
        path = event.get('path', '') or event.get('rawPath', '')
        path_parameters = event.get('pathParameters') or {}
        query_parameters = event.get('queryStringParameters') or {}
        body = event.get('body', '{}')
        
        # Parse body if it's a string
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {}
        
        # Normalize path for routing
        route_key = f"{http_method} {path}"
        
        with logfire.span(
            "lambda api parsed",
            method=http_method,
            path=path,
            path_params=path_parameters,
            query_params=query_parameters,
            route_key=route_key
        ):
            try:
                # City endpoints
                if route_key.startswith('POST /city') or route_key.startswith('POST /cities'):
                    return create_city(body)
                elif route_key.startswith('GET /city') or route_key.startswith('GET /cities'):
                    city_id = path_parameters.get('city_id') or query_parameters.get('city_id')
                    return get_city(city_id)
                elif route_key.startswith('PUT /city') or route_key.startswith('PUT /cities'):
                    city_id = path_parameters.get('city_id') or query_parameters.get('city_id')
                    return update_city(city_id, body)
                
                # Visit endpoints
                elif route_key.startswith('POST /city/') and '/visit' in route_key:
                    city_id = path_parameters.get('city_id')
                    return add_visit_to_city(city_id, body)
                elif route_key.startswith('PUT /city/') and '/visit' in route_key:
                    city_id = path_parameters.get('city_id')
                    trip = query_parameters.get('trip')
                    return update_visit_in_city(city_id, trip, body)
                
                else:
                    return create_response(404, {'message': f'Route not found: {route_key}'})

            except Exception as e:
                logfire.error("Error processing request:", error=e)
                import traceback
                logfire.error("Traceback", traceback=traceback.format_exc())
                return create_response(500, {'message': 'Internal Server Error', 'error': str(e)})


logfire.instrument_aws_lambda(lambda_handler)


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a standardized API response."""
    response = {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(body)
    }
    logfire.info("response", status_code=status_code)
    return response


def create_city_id(city_name: str, country: str, state: Optional[str] = None) -> str:
    """Create a unique city identifier."""
    if state:
        return f"{city_name},{state},{country}".lower().strip()
    return f"{city_name},{country}".lower().strip()


def geocode_city(city_name: str, country: str, state: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Geocode a city location."""
    # Build address string for geocoding
    address_parts = [city_name]
    if state:
        address_parts.append(state)
    address_parts.append(country)
    address = ", ".join(address_parts)
    
    with logfire.span("geocode_city", address=address):
        return geocode_address(address)


def create_city(body: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new city entry with optional visits."""
    with logfire.span("create_city", body=body):
        try:
            # Validate required fields
            city_name = body.get('city_name') or body.get('cityName')
            country = body.get('country')
            
            if not city_name or not country:
                return create_response(400, {
                    'message': 'Missing required fields: city_name and country are required'
                })
            
            state = body.get('state')
            city_id = create_city_id(city_name, country, state)
            
            # Check if city already exists
            existing_city = get_city_from_db(city_id)
            
            # Get visits from body if provided
            visits_data = body.get('visits', [])
            visits = []
            if visits_data:
                for visit_data in visits_data:
                    try:
                        visit = Visit(**visit_data)
                        visits.append(visit)
                    except Exception as e:
                        logfire.warning("Invalid visit data", visit_data=visit_data, error=str(e))
            
            # Geocode the city
            geocode_result = geocode_city(city_name, country, state)
            
            # Create city object
            city_data = {
                'city_id': city_id,
                'city_name': city_name,
                'country': country,
                'state': state,
                'visits': visits,
            }
            
            if geocode_result:
                city_data['latitude'] = Decimal(str(geocode_result['latitude']))
                city_data['longitude'] = Decimal(str(geocode_result['longitude']))
                city_data['location_name'] = geocode_result.get('location', '')
            
            city = City(**city_data)
            
            # Store in DynamoDB
            # Convert visits to dict for DynamoDB storage
            city_dict = city.model_dump(mode='json')
            if city_dict.get('visits'):
                city_dict['visits'] = [visit.model_dump(mode='json') if isinstance(visit, Visit) else visit 
                                      for visit in city_dict['visits']]
            
            city_storage = CityForStorage(**city_dict)
            table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
            store_result(city_storage, table_name, {"confirmation": city_id})
            
            logfire.info("City created successfully", city_id=city_id, city_name=city_name)
            
            return create_response(201, {
                'message': 'City created successfully',
                'city': city.model_dump(mode='json')
            })
            
        except Exception as e:
            logfire.error("Error creating city", error=str(e))
            return create_response(500, {'message': 'Error creating city', 'error': str(e)})


def get_city(city_id: Optional[str]) -> Dict[str, Any]:
    """Get a city by city_id."""
    with logfire.span("get_city", city_id=city_id):
        if not city_id:
            return create_response(400, {'message': 'city_id is required'})
        
        city_data = get_city_from_db(city_id)
        
        if not city_data:
            return create_response(404, {'message': f'City not found: {city_id}'})
        
        # Convert visits dicts to Visit objects
        if city_data.get('visits') and isinstance(city_data['visits'], list):
            city_data['visits'] = [Visit(**visit) if isinstance(visit, dict) else visit 
                                   for visit in city_data['visits']]
        
        # Convert to City model
        normalized_data = normalize_booking_data(city_data, City)
        city = City.model_construct(**normalized_data)
        
        return create_response(200, {'city': city.model_dump(mode='json')})


def update_city(city_id: Optional[str], body: Dict[str, Any]) -> Dict[str, Any]:
    """Update a city's basic information."""
    with logfire.span("update_city", city_id=city_id, body=body):
        if not city_id:
            return create_response(400, {'message': 'city_id is required'})
        
        city_data = get_city_from_db(city_id)
        if not city_data:
            return create_response(404, {'message': f'City not found: {city_id}'})
        
        # Convert visits dicts to Visit objects
        if city_data.get('visits') and isinstance(city_data['visits'], list):
            city_data['visits'] = [Visit(**visit) if isinstance(visit, dict) else visit 
                                   for visit in city_data['visits']]
        
        # Normalize and get existing city
        normalized_data = normalize_booking_data(city_data, City)
        city = City.model_construct(**normalized_data)
        
        # Update fields if provided
        if 'city_name' in body:
            city.city_name = body['city_name']
        if 'country' in body:
            city.country = body['country']
        if 'state' in body:
            city.state = body.get('state')
        
        # Re-geocode if location changed
        if any(key in body for key in ['city_name', 'country', 'state']):
            geocode_result = geocode_city(city.city_name, city.country, city.state)
            if geocode_result:
                city.latitude = Decimal(str(geocode_result['latitude']))
                city.longitude = Decimal(str(geocode_result['longitude']))
                city.location_name = geocode_result.get('location', '')
        
        # Store updated city
        city_dict = city.model_dump(mode='json')
        if city_dict.get('visits'):
            city_dict['visits'] = [visit.model_dump(mode='json') if isinstance(visit, Visit) else visit 
                                  for visit in city_dict['visits']]
        
        city_storage = CityForStorage(**city_dict)
        table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
        store_result(city_storage, table_name, {"confirmation": city_id})
        
        return create_response(200, {
            'message': 'City updated successfully',
            'city': city.model_dump(mode='json')
        })


def add_visit_to_city(city_id: Optional[str], body: Dict[str, Any]) -> Dict[str, Any]:
    """Add a visit to an existing city."""
    with logfire.span("add_visit_to_city", city_id=city_id, body=body):
        if not city_id:
            return create_response(400, {'message': 'city_id is required'})
        
        city_data = get_city_from_db(city_id)
        if not city_data:
            return create_response(404, {'message': f'City not found: {city_id}'})
        
        # Convert visits dicts to Visit objects
        if city_data.get('visits') and isinstance(city_data['visits'], list):
            city_data['visits'] = [Visit(**visit) if isinstance(visit, dict) else visit 
                                   for visit in city_data['visits']]
        
        # Get existing city
        normalized_data = normalize_booking_data(city_data, City)
        city = City.model_construct(**normalized_data)
        
        # Ensure visits list exists
        if city.visits is None:
            city.visits = []
        
        # Create new visit
        try:
            visit = Visit(**body)
            city.visits.append(visit)
        except Exception as e:
            return create_response(400, {
                'message': 'Invalid visit data',
                'error': str(e),
                'required_fields': ['start_date', 'end_date', 'trip']
            })
        
        # Store updated city
        city_dict = city.model_dump(mode='json')
        if city_dict.get('visits'):
            city_dict['visits'] = [visit.model_dump(mode='json') if isinstance(visit, Visit) else visit 
                                  for visit in city_dict['visits']]
        
        city_storage = CityForStorage(**city_dict)
        table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
        store_result(city_storage, table_name, {"confirmation": city_id})
        
        return create_response(200, {
            'message': 'Visit added successfully',
            'city': city.model_dump(mode='json')
        })


def update_visit_in_city(city_id: Optional[str], trip: Optional[str], body: Dict[str, Any]) -> Dict[str, Any]:
    """Update a specific visit in a city by trip name."""
    with logfire.span("update_visit_in_city", city_id=city_id, trip=trip, body=body):
        if not city_id:
            return create_response(400, {'message': 'city_id is required'})
        
        if not trip:
            return create_response(400, {'message': 'trip parameter is required'})
        
        city_data = get_city_from_db(city_id)
        if not city_data:
            return create_response(404, {'message': f'City not found: {city_id}'})
        
        # Convert visits dicts to Visit objects
        if city_data.get('visits') and isinstance(city_data['visits'], list):
            city_data['visits'] = [Visit(**visit) if isinstance(visit, dict) else visit 
                                   for visit in city_data['visits']]
        
        # Get existing city
        normalized_data = normalize_booking_data(city_data, City)
        city = City.model_construct(**normalized_data)
        
        # Ensure visits list exists
        if not city.visits:
            return create_response(404, {'message': f'No visits found for city: {city_id}'})
        
        # Find visit by trip
        visit_found = False
        for visit in city.visits:
            if visit.trip == trip:
                # Update visit fields
                if 'start_date' in body:
                    visit.start_date = body['start_date']
                if 'end_date' in body:
                    visit.end_date = body['end_date']
                if 'trip' in body:
                    visit.trip = body['trip']
                visit_found = True
                break
        
        if not visit_found:
            return create_response(404, {
                'message': f'Visit with trip "{trip}" not found in city: {city_id}'
            })
        
        # Store updated city
        city_dict = city.model_dump(mode='json')
        if city_dict.get('visits'):
            city_dict['visits'] = [visit.model_dump(mode='json') if isinstance(visit, Visit) else visit 
                                  for visit in city_dict['visits']]
        
        city_storage = CityForStorage(**city_dict)
        table_name = os.environ.get("BOOKINGS_TABLE_NAME", "bookings")
        store_result(city_storage, table_name, {"confirmation": city_id})
        
        return create_response(200, {
            'message': 'Visit updated successfully',
            'city': city.model_dump(mode='json')
        })


def get_city_from_db(city_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve city data from DynamoDB."""
    # Reuse the existing get_booking_by_confirmation function
    # since cities are stored with city_id as the confirmation key
    return get_booking_by_confirmation(city_id)
