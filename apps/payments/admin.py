from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Administration simple des paiements.
    """
    list_display = [
        'transaction_id',
        'order_link',
        'amount_display',
        'payment_method_badge',
        'status_badge',
        'paid_at',
        'created_at'
    ]
    
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'order__order_number', 'phone_number']
    ordering = ['-created_at']
    list_per_page = 25
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('transaction_id', 'order_link', 'amount', 'payment_method')
        }),
        ('Statut', {
            'fields': ('status', 'paid_at', 'failed_reason')
        }),
        ('Mobile Money', {
            'fields': ('phone_number', 'details'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['transaction_id', 'created_at', 'updated_at', 'order_link']
    
    def order_link(self, obj):
        """Lien cliquable vers la commande associée."""
        url = reverse('admin:orders_order_change', args=[obj.order.id])
        return format_html(
            '<a href="{}" style="font-weight: bold;">Commande #{}</a>',
            url,
            obj.order.order_number
        )
    order_link.short_description = 'Commande'
    
    def amount_display(self, obj):
        """Affiche le montant formaté."""
        return format_html(
            '<span style="font-weight: bold; color: #2c3e50;">{} FCFA</span>',
            f"{obj.amount:,.0f}".replace(',', ' ')
        )
    amount_display.short_description = 'Montant'
    amount_display.admin_order_field = 'amount'
    
    def payment_method_badge(self, obj):
        """Badge coloré pour la méthode de paiement."""
        colors = {
            'TMONEY': '#1976D2',
            'FLOOZ': '#4CAF50',
            'CASH': '#FF9800',
        }
        color = colors.get(obj.payment_method, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color,
            obj.get_payment_method_display()
        )
    payment_method_badge.short_description = 'Moyen'
    
    def status_badge(self, obj):
        """Badge coloré pour le statut."""
        colors = {
            'PENDING': '#FFC107',
            'SUCCESS': '#4CAF50',
            'FAILED': '#F44336',
        }
        color = colors.get(obj.status, '#757575')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Statut'
    
    actions = ['mark_as_success', 'mark_as_failed']
    
    def mark_as_success(self, request, queryset):
        """Marque les paiements sélectionnés comme réussis."""
        updated = queryset.update(status='SUCCESS', paid_at=timezone.now())
        self.message_user(request, f"{updated} paiement(s) marqué(s) comme réussi(s).")
    mark_as_success.short_description = "Marquer comme réussi"
    
    def mark_as_failed(self, request, queryset):
        """Marque les paiements sélectionnés comme échoués."""
        updated = queryset.update(status='FAILED')
        self.message_user(request, f"{updated} paiement(s) marqué(s) comme échoué(s).")
    mark_as_failed.short_description = "Marquer comme échoué"
    
    def get_queryset(self, request):
        """Optimisation avec select_related."""
        return super().get_queryset(request).select_related('order')