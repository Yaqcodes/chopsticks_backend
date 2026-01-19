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
