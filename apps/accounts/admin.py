from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Administration simple pour les utilisateurs.
    """
    list_display = ['phone_number', 'email', 'first_name', 'last_name', 'role', 'is_verified', 'is_active']
    list_filter = ['role', 'is_verified', 'is_active']
    search_fields = ['phone_number', 'email', 'first_name', 'last_name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('phone_number', 'email', 'first_name', 'last_name', 'avatar')
        }),
        ('Authentification', {
            'fields': ('password',)
        }),
        ('Rôle et statut', {
            'fields': ('role', 'is_verified', 'is_active', 'is_staff')
        }),
        ('Dates', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']