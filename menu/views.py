from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import connection
from django.db.models import Q, Case, When

from core.utils import get_business_from_request
from .models import Category, MenuItem


def filter_queryset_by_badge(queryset, badge):
    """Filter by badge in a way that works on SQLite and PostgreSQL (and other DBs)."""
    if not badge:
        return queryset
    # PostgreSQL (and MySQL) support JSONField __contains with list; SQLite does not.
    if connection.vendor == 'sqlite':
        # Match JSON array element e.g. ["bestseller"] or ["sale","bestseller"]
        return queryset.filter(badges__icontains=f'"{badge}"')
    return queryset.filter(badges__contains=[badge])
from .serializers import (
    CategorySerializer, MenuItemSerializer, MenuItemDetailSerializer,
    FeaturedItemsSerializer, MenuSearchSerializer
)


class CategoryListView(generics.ListAPIView):
    """List all active menu categories for the current business."""
    
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sort_order', 'name']
    ordering = ['sort_order']
    
    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        # Return categories for this business
        return Category.objects.filter(
            is_active=True,
            restaurant_settings=restaurant_settings
        ).distinct()


class CategoryDetailView(generics.RetrieveAPIView):
    """Get detailed information about a specific category."""
    
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        # Return categories for this business
        return Category.objects.filter(
            is_active=True,
            restaurant_settings=restaurant_settings
        ).distinct()


class MenuItemListView(generics.ListAPIView):
    """List all available menu items with filtering and search."""
    
    queryset = MenuItem.objects.filter(is_available=True)
    serializer_class = MenuItemSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_featured']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'sort_order']
    ordering = ['category', 'sort_order', 'name']
    
    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        queryset = MenuItem.objects.filter(
            is_available=True,
            restaurant_settings=restaurant_settings,
        )
        
        # Filter by category if provided
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by badge if provided
        badge = self.request.query_params.get('badge')
        queryset = filter_queryset_by_badge(queryset, badge)
        
        # Filter by price range if provided
        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')
        
        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)
        
        # Filter by explicit id list (e.g. SubCategories section). Preserve order.
        ids_param = self.request.query_params.get('ids')
        if ids_param:
            try:
                id_list = [int(x.strip()) for x in ids_param.split(',') if x.strip()]
                if id_list:
                    # Preserve order: filter by ids then order by position in id_list
                    ordering = self._order_by_ids(id_list)
                    queryset = queryset.filter(id__in=id_list).order_by(ordering)
            except (ValueError, TypeError):
                pass
        
        return queryset
    
    def _order_by_ids(self, id_list):
        """Return Case/When ordering so results match id_list order."""
        return Case(*[When(id=x, then=pos) for pos, x in enumerate(id_list)])


class MenuItemDetailView(generics.RetrieveAPIView):
    """Get detailed information about a specific menu item."""
    
    queryset = MenuItem.objects.filter(is_available=True)
    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        return MenuItem.objects.filter(
            is_available=True,
            restaurant_settings=restaurant_settings,
        )
    serializer_class = MenuItemDetailSerializer
    permission_classes = [AllowAny]


class FeaturedItemsView(generics.ListAPIView):
    """List all featured menu items."""
    
    queryset = MenuItem.objects.filter(is_available=True, is_featured=True)
    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        return MenuItem.objects.filter(
            is_available=True,
            is_featured=True,
            restaurant_settings=restaurant_settings,
        )
    serializer_class = FeaturedItemsSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['sort_order', 'name']
    ordering = ['sort_order']


@api_view(['GET'])
@permission_classes([AllowAny])
def menu_search(request):
    """Search menu items by name, description, or category."""
    
    restaurant_settings = get_business_from_request(request)
    query = request.query_params.get('q', '')
    if not query:
        return Response({'error': 'Search query is required.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Search in name, description, and category name
    queryset = MenuItem.objects.filter(
        Q(is_available=True) &
        Q(restaurant_settings=restaurant_settings) &
        (Q(name__icontains=query) | 
         Q(description__icontains=query) | 
         Q(category__name__icontains=query))
    ).distinct()
    
    # Apply additional filters if provided
    category_id = request.query_params.get('category_id')
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    
    queryset = filter_queryset_by_badge(queryset, request.query_params.get('badge'))
    
    # Serialize results
    serializer = MenuSearchSerializer(queryset, many=True)
    
    return Response({
        'query': query,
        'results': serializer.data,
        'count': queryset.count()
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def menu_by_category(request, category_id):
    """Get all menu items for a specific category."""
    
    restaurant_settings = get_business_from_request(request)
    try:
        # Validate category belongs to this business
        category = Category.objects.get(
            id=category_id,
            is_active=True,
            restaurant_settings=restaurant_settings
        )
    except Category.DoesNotExist:
        return Response({'error': 'Category not found.'}, status=status.HTTP_404_NOT_FOUND)
    
    menu_items = MenuItem.objects.filter(
        category=category,
        is_available=True,
        restaurant_settings=restaurant_settings,
    ).order_by('sort_order', 'name')
    
    category_serializer = CategorySerializer(category)
    menu_serializer = MenuItemSerializer(menu_items, many=True)
    
    return Response({
        'category': category_serializer.data,
        'menu_items': menu_serializer.data,
        'count': menu_items.count()
    })
