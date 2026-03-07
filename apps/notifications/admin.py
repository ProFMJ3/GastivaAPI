from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """
    Administration simple des notifications.
    """
    list_display = [
        'recipient',
        'title_preview',
        'type_badge',
        'priority_badge',
        'read_status',
        'created_at'
    ]
    
    list_filter = ['notification_type', 'priority', 'is_read', 'created_at']
    search_fields = ['recipient__email', 'recipient__phone_number', 'title', 'message']
    ordering = ['-created_at']
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Destinataire', {
            'fields': ('recipient',)
        }),
        ('Notification', {
            'fields': ('notification_type', 'priority', 'title', 'message')
        }),
        ('Statut', {
            'fields': ('is_read', 'read_at', 'expires_at')
        }),
        ('Données supplémentaires', {
            'fields': ('data',),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    actions = ['mark_as_read', 'mark_as_unread', 'delete_expired']
    
    def title_preview(self, obj):
        """Aperçu du titre."""
        if len(obj.title) > 40:
            return f"{obj.title[:40]}..."
        return obj.title
    title_preview.short_description = 'Titre'
    
    def type_badge(self, obj):
        """Badge coloré pour le type."""
        colors = {
            'ORDER': '#2196F3',
            'PAYMENT': '#4CAF50',
            'OFFER': '#FF9800',
            'WELCOME': '#9C27B0',
        }
        # Prendre le premier mot du type comme clé
        base_type = obj.notification_type.split('_')[0]
        color = colors.get(base_type, '#757575')
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 6px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_notification_type_display()
        )
    type_badge.short_description = 'Type'
    
    def priority_badge(self, obj):
        """Badge coloré pour la priorité."""
        colors = {
            'LOW': '#757575',
            'MEDIUM': '#2196F3',
            'HIGH': '#FF9800',
            'URGENT': '#F44336',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.priority, '#757575'),
            obj.get_priority_display()
        )
    priority_badge.short_description = 'Priorité'
    
    def read_status(self, obj):
        """Indicateur de lecture."""
        if obj.is_read:
            return format_html(
                '<span style="color: green;">✓ Lu</span><br/><small>{}</small>',
                obj.read_at.strftime('%d/%m %H:%M') if obj.read_at else ''
            )
        return format_html('<span style="color: orange;">○ Non lu</span>')
    read_status.short_description = 'Statut'
    
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True, read_at=timezone.now())
        self.message_user(request, f"{updated} notification(s) marquée(s) comme lue(s).")
    mark_as_read.short_description = "Marquer comme lues"
    
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False, read_at=None)
        self.message_user(request, f"{updated} notification(s) marquée(s) comme non lue(s).")
    mark_as_unread.short_description = "Marquer comme non lues"
    
    def delete_expired(self, request, queryset):
        now = timezone.now()
        expired = queryset.filter(expires_at__lt=now)
        count = expired.count()
        expired.delete()
        self.message_user(request, f"{count} notification(s) expirée(s) supprimée(s).")
    delete_expired.short_description = "Supprimer les expirées"


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    """
    Administration simple des préférences.
    """
    list_display = ['user', 'push', 'email', 'sms', 'in_app', 'updated_at']
    list_filter = ['allow_push', 'allow_email', 'allow_sms', 'allow_in_app']
    search_fields = ['user__email', 'user__phone_number']
    ordering = ['-updated_at']
    
    def push(self, obj):
        return format_html(
            '<span style="color: {};">✓</span>' if obj.allow_push else '<span style="color: #ccc;">✗</span>',
            'green' if obj.allow_push else '#ccc'
        )
    push.short_description = 'Push'
    
    def email(self, obj):
        return format_html(
            '<span style="color: {};">✓</span>' if obj.allow_email else '<span style="color: #ccc;">✗</span>',
            'green' if obj.allow_email else '#ccc'
        )
    email.short_description = 'Email'
    
    def sms(self, obj):
        return format_html(
            '<span style="color: {};">✓</span>' if obj.allow_sms else '<span style="color: #ccc;">✗</span>',
            'green' if obj.allow_sms else '#ccc'
        )
    sms.short_description = 'SMS'
    
    def in_app(self, obj):
        return format_html(
            '<span style="color: {};">✓</span>' if obj.allow_in_app else '<span style="color: #ccc;">✗</span>',
            'green' if obj.allow_in_app else '#ccc'
        )
    in_app.short_description = 'In-App'