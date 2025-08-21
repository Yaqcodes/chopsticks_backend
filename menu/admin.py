from django.contrib import admin
from unfold.admin import ModelAdmin as UnfoldModelAdmin
from .models import Category, MenuItem


@admin.register(Category)
class CategoryAdmin(UnfoldModelAdmin):
    """Admin interface for Category model."""
    
    list_display = ['name', 'is_active', 'sort_order', 'menu_items_count', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['sort_order', 'name']
    list_editable = ['is_active', 'sort_order']
    
    def menu_items_count(self, obj):
        """Display count of menu items in category."""
        return obj.menu_items.count()
    menu_items_count.short_description = 'Menu Items'


@admin.register(MenuItem)
class MenuItemAdmin(UnfoldModelAdmin):
    """Admin interface for MenuItem model."""
    
    list_display = ['name', 'category', 'price', 'is_available', 'is_featured', 'sort_order']
    list_filter = ['category', 'is_available', 'is_featured', 'badges', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    ordering = ['category', 'sort_order', 'name']
    list_editable = ['is_available', 'is_featured', 'sort_order']
    filter_horizontal = []
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'category', 'price', 'image')
        }),
        ('Status & Display', {
            'fields': ('is_available', 'is_featured', 'sort_order', 'preparation_time')
        }),
        ('Additional Information', {
            'fields': ('badges', 'allergens', 'nutritional_info'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('category')
