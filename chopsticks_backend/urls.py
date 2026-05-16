"""
URL configuration for chopsticks_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from core.admin_sites import roschi_admin_site, chopsticks_admin_site, zmall_admin_site
from core.main_admin_site import main_admin_site


def healthz(_request):
    """Lightweight liveness probe for Railway/uptime checks (no DB or auth)."""
    return JsonResponse({'status': 'ok'})

# Swagger/OpenAPI Schema
schema_view = get_schema_view(
    openapi.Info(
        title="Chopsticks & Bowls API",
        default_version='v1',
        description="Complete API documentation for Chopsticks & Bowls restaurant backend",
        terms_of_service="https://www.chopsticksandbowls.com/terms/",
        contact=openapi.Contact(email="api@chopsticksandbowls.com"),
        license=openapi.License(name="Proprietary License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

# When using S3-compatible storage (Railway buckets, etc.) media URLs point at the
# bucket directly, so we MUST NOT mount /media/ from disk in production. Only mount
# it when uploads live on the local filesystem (legacy / local dev).
urlpatterns = []
if not getattr(settings, 'USE_S3_STORAGE', False) and settings.MEDIA_URL:
    urlpatterns += list(static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT))
urlpatterns += [
    # Liveness probe (Railway healthcheck path).
    path('healthz/', healthz, name='healthz'),

    # Root redirect to user guide
    path('', include('core.urls')),
    
    # Main admin interface (superusers only)
    path('admin/', main_admin_site.urls),
    
    # Business-specific admin interfaces
    path('roschi-admin/', roschi_admin_site.urls),
    path('cb-admin/', chopsticks_admin_site.urls),
    path('zmall-admin/', zmall_admin_site.urls),
    
    # Loyalty admin routes
    path('admin-qr/', include('loyalty.admin_urls')),
    
    # User Guide (easily accessible)
    path('guide/', include('core.urls')),
    
    # API Documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API endpoints
    path('api/core/', include('core.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/menu/', include('menu.urls')),
    path('api/', include('menu.product_urls')),
    path('api/orders/', include('orders.urls')),
    path('api/loyalty/', include('loyalty.urls')),
    path('api/payments/', include('payments.urls')),
    path('api/promotions/', include('promotions.urls')),
    path('api/addresses/', include('addresses.urls')),
    path('api/storefront/', include('storefront.urls')),
]
# Static files in production are served by WhiteNoise; only mount the dev fallback
# when DEBUG=True so production never re-serves collected static via runserver paths.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Main admin site is already configured in core/main_admin_site.py
