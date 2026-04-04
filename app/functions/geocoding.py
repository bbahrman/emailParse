"""
Geocoding utility using Nominatim/geopy.
"""
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from typing import Optional, Dict, Any
import logfire

geolocator = Nominatim(user_agent="email-parse-booking-geocoder")


def geocode_address(address: str) -> Optional[Dict[str, Any]]:
    if not address or not address.strip():
        logfire.info("Empty address provided for geocoding")
        return None

    with logfire.span("geocode_address", address=address):
        try:
            location = geolocator.geocode(address, timeout=10)

            if location:
                result = {
                    "latitude": location.latitude,
                    "longitude": location.longitude,
                    "location": location.address,
                    "raw": location.raw if hasattr(location, "raw") else None,
                }
                logfire.info(
                    "Successfully geocoded address",
                    address=address,
                    latitude=result["latitude"],
                    longitude=result["longitude"],
                )
                return result
            else:
                logfire.warning("No location found for address", address=address)
                return None

        except GeocoderTimedOut:
            logfire.error("Geocoding timed out", address=address)
            return None
        except GeocoderServiceError as e:
            logfire.error("Geocoding service error", address=address, error=str(e))
            return None
        except Exception as e:
            logfire.error(
                "Unexpected error geocoding address",
                address=address,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None
