"""
Sighting service for Firestore database operations.
"""
import logging
from typing import Optional, List
from google.cloud import firestore

from ..models.sighting import SightingResponse, Location
from ..exceptions import ServiceUnavailableError
from .. import gcp_clients

logger = logging.getLogger(__name__)


class SightingService:
    """Service for managing dog sightings in Firestore."""
    
    def __init__(self, firestore_client=None):
        """
        Initialize sighting service.
        
        Args:
            firestore_client: Firestore client (or None to use global client)
        """
        self.firestore = firestore_client or gcp_clients.firestore_client
        self.collection_name = "sightings"
    
    def create_sighting(self, sighting_data: dict) -> str:
        """
        Create a new sighting in Firestore.
        
        Args:
            sighting_data: Dictionary with sighting fields
            
        Returns:
            str: Document ID of created sighting
            
        Raises:
            ServiceUnavailableError: If Firestore client is not initialized
        """
        if not self.firestore:
            raise ServiceUnavailableError("Firestore")
        
        try:
            doc_ref = self.firestore.collection(self.collection_name).document()
            doc_ref.set(sighting_data)
            logger.info(f"Created sighting document: {doc_ref.id}")
            return doc_ref.id
        except Exception as e:
            logger.error(f"Failed to create sighting: {e}")
            raise
    
    def get_sightings(self, filters: Optional[dict] = None, 
                     cursor: Optional[str] = None, limit: int = 10) -> dict:
        """
        Query sightings with filtering and pagination.
        
        Args:
            filters: Optional dict with 'start_date', 'end_date', 'bounds' (north/south/east/west)
            cursor: Optional document ID to start after (for pagination)
            limit: Maximum number of results to return
            
        Returns:
            dict: Contains 'data' (list of sightings) and 'next_cursor'
            
        Raises:
            ServiceUnavailableError: If Firestore client is not initialized
        """
        if not self.firestore:
            raise ServiceUnavailableError("Firestore")
        
        filters = filters or {}
        query = self._build_query(filters)
        
        # Handle cursor pagination
        if cursor:
            cursor_doc_ref = self.firestore.collection(self.collection_name).document(cursor)
            cursor_doc = cursor_doc_ref.get()
            if cursor_doc.exists:
                query = query.start_after(cursor_doc)
        
        # Execute query with deep scan for geo filtering
        sightings = []
        last_scanned_doc = None
        bounds = filters.get('bounds')
        
        # Deep scan loop to handle geo filtering
        BATCH_SIZE = 50
        while len(sightings) < limit:
            current_query = query.limit(BATCH_SIZE)
            docs = list(current_query.stream())
            
            if not docs:
                break
            
            for doc in docs:
                last_scanned_doc = doc
                data = doc.to_dict()
                
                # Apply geo filter if bounds are provided
                if bounds and not self._is_within_bounds(data, bounds):
                    continue
                
                # Convert to response format
                sighting = SightingResponse.from_firestore_doc(doc.id, data)
                sightings.append(sighting.to_dict())
                
                if len(sightings) >= limit:
                    break
            
            # Continue query from last doc if we need more results
            if len(sightings) < limit and docs:
                query = self._rebuild_query_from_doc(filters, docs[-1])
            elif not docs:
                break
        
        next_cursor = last_scanned_doc.id if last_scanned_doc and len(sightings) == limit else None
        
        return {
            "data": sightings,
            "next_cursor": next_cursor
        }
    
    def _build_query(self, filters: dict):
        """
        Build Firestore query from filters.
        
        Args:
            filters: Dictionary with optional 'start_date', 'end_date' keys
            
        Returns:
            Query: Firestore query object
        """
        query = self.firestore.collection(self.collection_name)
        query = query.order_by("sighting_date", direction=firestore.Query.DESCENDING)
        query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)
        
        if 'start_date' in filters and filters['start_date']:
            query = query.where("sighting_date", ">=", filters['start_date'])
        
        if 'end_date' in filters and filters['end_date']:
            query = query.where("sighting_date", "<=", filters['end_date'])
        
        return query
    
    def _rebuild_query_from_doc(self, filters: dict, last_doc):
        """Rebuild query and start after the last document."""
        query = self._build_query(filters)
        return query.start_after(last_doc)
    
    def _is_within_bounds(self, sighting_data: dict, bounds: dict) -> bool:
        """
        Check if sighting location is within geographic bounds.
        
        Args:
            sighting_data: Firestore document data
            bounds: Dict with 'north', 'south', 'east', 'west' keys
            
        Returns:
            bool: True if within bounds, False otherwise
        """
        location = sighting_data.get("location")
        if not location:
            return False
        
        lat = location.latitude
        lng = location.longitude
        
        # Check latitude bounds
        if not (bounds['south'] <= lat <= bounds['north']):
            return False
        
        # Check longitude bounds (handle dateline crossing)
        west = bounds['west']
        east = bounds['east']
        
        if west <= east:
            # Normal case (doesn't cross dateline)
            lng_match = west <= lng <= east
        else:
            # Crosses dateline
            lng_match = west <= lng or lng <= east
        
        return lng_match
