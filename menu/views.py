from rest_framework import generics, status, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAdminUser  # or your custom permission
from .serializers import CategoryWriteSerializer, MenuItemWriteSerializer

from core.utils import get_business_from_request
from .catalog_queryset import (
    apply_menu_item_style_filters_and_sort,
    filter_queryset_by_badge,
    menu_items_base_catalog_queryset,
)
from .models import Category, MenuItem
from .pagination import MenuItemPageNumberPagination
from .serializers import (
    CategorySerializer, MenuItemSerializer, MenuItemDetailSerializer,
    FeaturedItemsSerializer, MenuSearchSerializer,
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
    pagination_class = MenuItemPageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_featured']
    search_fields = ['name', 'description', 'barcode']

    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        return menu_items_base_catalog_queryset(self.request, restaurant_settings)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return apply_menu_item_style_filters_and_sort(queryset, self.request)


@api_view(['GET'])
@permission_classes([AllowAny])
def menu_item_filter_options(request):
    """
    Distinct color names and sizes for the current catalog scope (category, search, sale, gender, etc.)
    without applying colour/size/price/sort — one request for filter dropdowns.
    """
    restaurant_settings = get_business_from_request(request)
    qs = menu_items_base_catalog_queryset(request, restaurant_settings)
    search = request.query_params.get('search', '').strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
            | Q(barcode__icontains=search)
        )
    names = set()
    sizes_out = set()
    for colors, size in qs.values_list('colors', 'size').iterator(chunk_size=500):
        if colors and isinstance(colors, list):
            for c in colors:
                if isinstance(c, dict):
                    name = (c.get('name') or '').strip()
                    if name:
                        names.add(name)
        if size and str(size).strip():
            sizes_out.add(str(size).strip())
    return Response({
        'colors': sorted(names, key=str.lower),
        'sizes': sorted(sizes_out, key=str.lower),
    })


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
    
    # Search in name, description, category name, and barcode
    queryset = MenuItem.objects.filter(
        Q(is_available=True) &
        Q(restaurant_settings=restaurant_settings) &
        (Q(name__icontains=query) | 
         Q(description__icontains=query) | 
         Q(category__name__icontains=query) |
         Q(barcode__icontains=query)) # Added barcode search
    ).distinct()
    
    # Apply additional filters if provided
    category_id = request.query_params.get('category_id')
    category_slug = request.query_params.get('category_slug')
    if category_id:
        queryset = queryset.filter(category_id=category_id)
    elif category_slug:
        category = Category.objects.filter(
            restaurant_settings=restaurant_settings,
            slug=category_slug.strip()
        ).first()
        if category:
            queryset = queryset.filter(category=category)

    queryset = filter_queryset_by_badge(queryset, request.query_params.get('badge'))

    on_sale_param = request.query_params.get('on_sale')
    if on_sale_param is not None and str(on_sale_param).strip().lower() in ('1', 'true', 'yes'):
        queryset = queryset.filter(on_sale=True)
    
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

@api_view(['GET'])
@permission_classes([AllowAny])
def menu_item_by_barcode(request, barcode):
    """Fetch a single menu item by its exact barcode."""
    
    restaurant_settings = get_business_from_request(request)
    
    try:
        # We use .get() because barcodes should be unique per item
        menu_item = MenuItem.objects.get(
            barcode=barcode,
            is_available=True,
            restaurant_settings=restaurant_settings
        )
    except MenuItem.DoesNotExist:
        return Response(
            {'error': 'No product found with this barcode.'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Use the detail serializer to provide the full picture (images, etc.)
    serializer = MenuItemDetailSerializer(menu_item)
    
    return Response(serializer.data)


# --- Category Mutation Views ---

class CategoryCreateView(generics.CreateAPIView):
    """POST /api/menu/categories/create/"""
    serializer_class = CategoryWriteSerializer
    permission_classes = [IsAdminUser]  # replace with your permission

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['restaurant_settings'] = get_business_from_request(self.request)
        return ctx


class CategoryUpdateView(generics.UpdateAPIView):
    """PUT/PATCH /api/menu/categories/{id}/update/"""
    serializer_class = CategoryWriteSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        return Category.objects.filter(restaurant_settings=restaurant_settings)

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['restaurant_settings'] = get_business_from_request(self.request)
        return ctx


class CategoryDeleteView(generics.DestroyAPIView):
    """DELETE /api/menu/categories/{id}/delete/"""
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        return Category.objects.filter(restaurant_settings=restaurant_settings)


# --- MenuItem Mutation Views ---

class MenuItemCreateView(generics.CreateAPIView):
    """POST /api/menu/items/create/"""
    serializer_class = MenuItemWriteSerializer
    permission_classes = [IsAdminUser]

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['restaurant_settings'] = get_business_from_request(self.request)
        return ctx

    def perform_create(self, serializer):
        restaurant_settings = get_business_from_request(self.request)
        serializer.save(restaurant_settings=restaurant_settings)


class MenuItemUpdateView(generics.UpdateAPIView):
    serializer_class = MenuItemWriteSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        return MenuItem.objects.filter(restaurant_settings=restaurant_settings)

    def get_object(self):
        queryset = self.get_queryset()
        if 'pk' in self.kwargs:
            obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
        else:
            obj = get_object_or_404(queryset, barcode=self.kwargs['barcode'])
        self.check_object_permissions(self.request, obj)
        return obj

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['restaurant_settings'] = get_business_from_request(self.request)
        return ctx


class MenuItemDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        restaurant_settings = get_business_from_request(self.request)
        return MenuItem.objects.filter(restaurant_settings=restaurant_settings)

    def get_object(self):
        queryset = self.get_queryset()
        if 'pk' in self.kwargs:
            obj = get_object_or_404(queryset, pk=self.kwargs['pk'])
        else:
            obj = get_object_or_404(queryset, barcode=self.kwargs['barcode'])
        self.check_object_permissions(self.request, obj)
        return obj
