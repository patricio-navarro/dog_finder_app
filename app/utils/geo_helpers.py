"""
Geographic helper utilities for boundary checking.
"""


def is_within_bounds(lat: float, lng: float, north: float, south: float, 
                    east: float, west: float) -> bool:
    """
    Check if coordinates are within geographic bounds.
    
    Args:
        lat: Latitude to check
        lng: Longitude to check
        north: Northern boundary
        south: Southern boundary
        east: Eastern boundary
        west: Western boundary
        
    Returns:
        bool: True if coordinates are within bounds
    """
    # Check latitude
    if not (south <= lat <= north):
        return False
    
    # Check longitude (handle dateline crossing)
    if west <= east:
        # Normal case
        return west <= lng <= east
    else:
        # Crosses dateline (e.g., west=170, east=-170)
        return west <= lng or lng <= east


def handles_dateline_crossing(west: float, east: float) -> bool:
    """
    Detect if bounds cross the international dateline.
    
    Args:
        west: Western longitude boundary
        east: Eastern longitude boundary
        
    Returns:
        bool: True if bounds cross the dateline
    """
    return west > east
