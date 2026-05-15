from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from core.utils import get_business_from_request

from .models import SpotlightPlacement
from .services import build_spotlights_payload


ALLOWED_PLACEMENTS = {choice.value for choice in SpotlightPlacement}


@api_view(['GET'])
@permission_classes([AllowAny])
def spotlight_list(request):
    """
    List active spotlight posts for the requesting tenant and placement.

    Query params:
      placement (required): e.g. shop_the_look, homepage_carousel
    """
    placement = (request.query_params.get('placement') or '').strip()
    if not placement:
        return Response(
            {'detail': 'Query parameter "placement" is required.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if placement not in ALLOWED_PLACEMENTS:
        return Response(
            {'detail': f'Unknown placement. Allowed: {", ".join(sorted(ALLOWED_PLACEMENTS))}.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    restaurant_settings = get_business_from_request(request)
    payload = build_spotlights_payload(restaurant_settings, placement)
    return Response(payload)
