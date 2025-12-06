"""
Geocoding service for converting coordinates to location details.
"""
import logging
from typing import Optional

from ..models.sighting import Location
from ..exceptions import GeocodingError, ServiceUnavailableError
from .. import gcp_clients

logger = logging.getLogger(__name__)


class GeocodingService:
    """Service for reverse geocoding operations."""
    
    def __init__(self, gmaps_client=None):
        """
        Initialize geocoding service.
        
        Args:
            gmaps_client: Google Maps client (or None to use global client)
        """
        self.gmaps = gmaps_client or gcp_clients.gmaps
    
    def reverse_geocode(self, latitude: float, longitude: float) -> Location:
        """
        Get location details from coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            
        Returns:
            Location: Location object with city, region, country populated
            
        Raises:
            ServiceUnavailableError: If gmaps client is not initialized
            GeocodingError: If geocoding fails
        """
        # Create base location with coordinates
        location = Location(
            latitude=latitude,
            longitude=longitude,
            city="",
            region="",
            country=""
        )
        
        # If no gmaps client, return location with empty address fields
        if not self.gmaps:
            logger.warning("Google Maps client not initialized, skipping geocoding")
            return location
        
        try:
            results = self.gmaps.reverse_geocode((latitude, longitude))
            
            if results:
                # Parse the first result
                address_components = results[0].get('address_components', [])
                parsed = self._parse_address_components(address_components)
                
                location.city = parsed.get('city', '')
                location.region = parsed.get('region', '')
                location.country = parsed.get('country', '')
                
                logger.info(f"Geocoded ({latitude}, {longitude}) to {location.city}, {location.region}, {location.country}")
            else:
                logger.warning(f"No geocoding results for ({latitude}, {longitude})")
                
        except Exception as e:
            # Log error but don't fail - we can still store the sighting without address details
            logger.error(f"Geocoding failed for ({latitude}, {longitude}): {e}")
        
        return location
    
    def _parse_address_components(self, components: list) -> dict:
        """
        Extract city, region, country from Google Maps address components.
        
        Args:
            components: List of address component dictionaries from Google Maps API
            
        Returns:
            dict: Parsed address with 'city', 'region', 'country' keys
        """
        parsed = {'city': '', 'region': '', 'country': ''}
        
        for component in components:
            types = component.get('types', [])
            long_name = component.get('long_name', '')
            
            if 'locality' in types:
                parsed['city'] = long_name
            elif 'administrative_area_level_1' in types:
                parsed['region'] = long_name
            elif 'country' in types:
                parsed['country'] = long_name
        
        return parsed
