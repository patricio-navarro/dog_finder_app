"""
URL helper utilities for the Dog Finder application.
"""


def gs_to_public_url(gs_url: str) -> str:
    """
    Convert gs:// URL to public HTTPS URL.
    
    Args:
        gs_url: GCS URL in format gs://bucket/path/to/file
        
    Returns:
        str: Public HTTPS URL or original URL if conversion fails
    """
    if not gs_url or not gs_url.startswith("gs://"):
        return gs_url
    
    try:
        # Remove gs:// prefix and split into bucket/path
        path = gs_url.replace("gs://", "")
        parts = path.split("/", 1)
        
        if len(parts) == 2:
            bucket, file_path = parts
            return f"https://storage.googleapis.com/{bucket}/{file_path}"
        else:
            return gs_url
    except Exception:
        return gs_url
