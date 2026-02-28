from django.contrib import admin
from .models import CategoryPartner, Partner


@admin.register(CategoryPartner)
class CategoryPartnerAdmin(admin.ModelAdmin):
    """Simple admin for partner categories."""
    list_display = ['name', 'icon', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    """Simple admin for partners."""
    list_display = ['name', 'category', 'quarter', 'phone', 'status']
    list_filter = ['status', 'category', 'quarter']
    search_fields = ['name', 'phone', 'email']
    fieldsets = (
        ('Info', {
            'fields': ('owner', 'name', 'category', 'description')
        }),
        ('Contact', {
            'fields': ('address', 'quarter', 'phone', 'email')
        }),
        ('Hours', {
            'fields': ('opening_time', 'closing_time', 'working_days')
        }),
        ('Status', {
            'fields': ('status',)
        }),
    )