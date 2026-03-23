# Core utilities for business identification

import logging
from urllib.parse import urlparse

from .models import RestaurantSettings

logger = logging.getLogger(__name__)


def get_business_from_request(request):
    """
    Identify business from frontend origin (where the request comes FROM).
    
    For shared backend architecture, we identify businesses by the frontend domain
    that made the request, not the backend domain that received it.
    
    Strict multi-tenancy: Frontend domain must be configured in RestaurantSettings.
    No fallbacks or defaults allowed.
    
    Identification Strategy:
    1. Extract frontend domain from Origin header (most reliable for CORS requests)
    2. Fallback to Referer header (for same-origin requests)
    3. Last resort: Host header (only works if each business has its own backend subdomain)
    
    Matching logic:
    1. Exact domain match (e.g., origin: 'https://roschiwater.com' matches domain: 'roschiwater.com')
    2. Subdomain match (e.g., origin: 'https://www.roschiwater.com' matches domain: 'roschiwater.com')
       - Checks if frontend domain ends with configured domain
    3. If multiple matches, prefer exact match
    """
    frontend_domain = None
    
    # Strategy 1: Try Origin header first (most reliable for CORS requests)
    origin = request.headers.get('Origin')
    if origin:
        try:
            parsed = urlparse(origin)
            frontend_domain = parsed.netloc.split(':')[0].lower()  # Remove port if present
            logger.debug("Extracted frontend domain from Origin header: %s", frontend_domain)
        except (ValueError, AttributeError) as e:
            logger.warning("Failed to parse Origin header: %s", str(e))
    
    # Strategy 2: Fallback to Referer header (for same-origin requests)
    if not frontend_domain:
        referer = request.headers.get('Referer')
        if referer:
            try:
                parsed = urlparse(referer)
                frontend_domain = parsed.netloc.split(':')[0].lower()
                logger.debug("Extracted frontend domain from Referer header: %s", frontend_domain)
            except (ValueError, AttributeError) as e:
                logger.warning("Failed to parse Referer header: %s", str(e))
    
    # Strategy 3: Last resort - use Host header (only works if each business has its own backend subdomain)
    if not frontend_domain:
        host = request.get_host()
        frontend_domain = host.split(':')[0].lower()
        logger.debug("Using Host header as fallback: %s", frontend_domain)
        logger.warning(
            "Using Host header for business identification. This only works if each business "
            "has its own backend subdomain. For shared backend, ensure Origin/Referer headers are sent."
        )
    
    if not frontend_domain:
        logger.error("Could not extract frontend domain from request headers")
        raise ValueError(
            "Could not identify business: No Origin or Referer header found. "
            "Frontend domain must be sent in request headers for business identification."
        )

    # Try exact domain match first
    try:
        return RestaurantSettings.objects.get(domain=frontend_domain)
    except RestaurantSettings.DoesNotExist:
        pass
    
    # Try subdomain match: find RestaurantSettings where frontend domain ends with configured domain
    # Example: frontend 'www.roschiwater.com' should match domain 'roschiwater.com'
    matches = []
    for settings in RestaurantSettings.objects.all():
        if settings.domain:
            if frontend_domain.endswith('.' + settings.domain) or frontend_domain == settings.domain:
                matches.append(settings)
    
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        # If multiple matches, prefer exact match
        exact_match = next((m for m in matches if m.domain == frontend_domain), None)
        if exact_match:
            return exact_match
        logger.warning("Multiple RestaurantSettings match domain '%s', using first: %s", frontend_domain, matches[0].domain)
        return matches[0]
    
    # No match found - this is a hard error for multi-tenancy
    logger.error("Business not found for frontend domain: %s", frontend_domain)
    raise ValueError(
        f"Business not found for frontend domain: {frontend_domain}. "
        f"Please configure domain in RestaurantSettings. "
        f"Available domains: {list(RestaurantSettings.objects.values_list('domain', flat=True))}"
    )


def get_frontend_url_from_business(restaurant_settings, request=None):
    """
    Get frontend URL for a business from RestaurantSettings.
    
    Constructs the frontend URL from the domain field, preserving protocol
    and subdomain from the original request when possible.
    
    Strict multi-tenancy: domain must be configured.
    
    Args:
        restaurant_settings: RestaurantSettings instance
        request: Optional Django request object to preserve original URL details
        
    Returns:
        str: Frontend URL (e.g., 'https://roschiwater.com' or 'http://localhost:5173')
        
    Raises:
        ValueError: If restaurant_settings is None or domain is not configured
    """
    if not restaurant_settings:
        raise ValueError("RestaurantSettings is required for frontend URL")
    
    if not restaurant_settings.domain:
        raise ValueError(
            f"Domain not configured for business '{restaurant_settings.name}'. "
            f"Please configure domain in RestaurantSettings."
        )
    
    domain = restaurant_settings.domain.strip()
    
    # Strip protocol if present for domain matching
    domain_for_matching = domain.lower()
    if domain_for_matching.startswith('http://') or domain_for_matching.startswith('https://'):
        domain_for_matching = urlparse(domain).netloc.split(':')[0]
        domain = domain_for_matching  # Use cleaned domain for processing
    
    # Handle development/localhost
    if 'localhost' in domain_for_matching or '127.0.0.1' in domain_for_matching:
        # For localhost, use HTTP and preserve port if in request
        if request:
            origin = request.headers.get('Origin') or request.headers.get('Referer')
            if origin:
                try:
                    parsed = urlparse(origin)
                    if 'localhost' in parsed.netloc.lower() or '127.0.0.1' in parsed.netloc.lower():
                        protocol = parsed.scheme or 'http'
                        port = f":{parsed.port}" if parsed.port else ''
                        return f"{protocol}://{parsed.netloc}{port}"
                except (ValueError, AttributeError) as e:
                    logger.debug("Failed to parse origin for localhost: %s", str(e))
        # Default localhost URL (Vite dev server typically runs on 5173)
        if ':5173' not in domain and ':' not in domain:
            return "http://localhost:5173"
        return f"http://{domain}" if not domain.startswith('http') else domain
    
    # Production: Try to preserve protocol and subdomain from request
    if request:
        origin = request.headers.get('Origin') or request.headers.get('Referer')
        if origin:
            try:
                parsed = urlparse(origin)
                original_domain = parsed.netloc.split(':')[0].lower()
                stored_domain = domain.lower()
                
                # If original domain matches or is a subdomain of stored domain
                if original_domain == stored_domain or original_domain.endswith('.' + stored_domain):
                    protocol = parsed.scheme or 'https'
                    return f"{protocol}://{original_domain}"
            except (ValueError, AttributeError) as e:
                logger.debug("Failed to parse origin for production URL: %s", str(e))
    
    # Fallback: construct from stored domain (assume HTTPS in production)
    if not domain.startswith('http'):
        return f"https://{domain}"
    return domain
