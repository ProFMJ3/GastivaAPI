from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from django.db import models
from django import forms
from .models import Order, OrderItem


class OrderItemInlineForm(forms.ModelForm):
    """Formulaire personnalisé pour OrderItem inline"""
    
    class Meta:
        model = OrderItem
        fields = ['offer', 'quantity']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rendre unit_price en lecture seule et le cacher
        self.fields['unit_price'] = forms.DecimalField(
            required=False,
            widget=forms.HiddenInput(),
            disabled=True
        )
    
    def save(self, commit=True):
        """Sauvegarde en définissant automatiquement unit_price depuis l'offre"""
        instance = super().save(commit=False)
        
        # Récupérer le prix depuis l'offre
        if instance.offer:
            instance.unit_price = instance.offer.discounted_price
        
        if commit:
            instance.save()
        return instance


class OrderItemInline(admin.TabularInline):
    """Inline pour ajouter/modifier les articles d'une commande"""
    model = OrderItem
    form = OrderItemInlineForm
    extra = 1
    can_delete = True
    fields = ['offer', 'quantity', 'unit_price_display', 'subtotal_display']
    readonly_fields = ['unit_price_display', 'subtotal_display']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('offer')
    
    def unit_price_display(self, obj):
        """Afficher le prix unitaire (lecture seule)"""
        if obj.offer:
            return format_html(
                '<span style="color: #666;">{}</span>',
                obj.offer.discounted_price
            )
        return "-"
    unit_price_display.short_description = 'Prix unitaire'
    
    def subtotal_display(self, obj):
        """Afficher le sous-total"""
        if obj.pk and obj.subtotal:
            return format_html('<strong>{}</strong>', obj.subtotal)
        elif obj.offer and obj.quantity:
            # Calculer le sous-total même avant sauvegarde
            subtotal = obj.offer.discounted_price * obj.quantity
            return format_html('<span style="color: #999;">({})</span>', subtotal)
        return "-"
    subtotal_display.short_description = 'Sous-total'
    
    def has_add_permission(self, request, obj=None):
        """Permet l'ajout uniquement si la commande existe"""
        return obj is not None


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Administration des commandes"""
    
    list_display = [
        'order_number', 
        'client_link', 
        'partner_link', 
        'status_colored', 
        'total_amount_display', 
        'item_count',
        'created_at'
    ]
    
    list_filter = [
        'status', 
        'created_at', 
        'confirmed_at', 
        'picked_up_at'
    ]
    
    search_fields = [
        'order_number', 
        'client__email', 
        'client__first_name', 
        'client__last_name',
        'partner__name',
        'pickup_code'
    ]
    
    readonly_fields = [
        'order_number',
        'pickup_code',
        'created_at',
        'updated_at',
        'confirmed_at',
        'picked_up_at',
        'cancelled_at',
        'total_amount_display',
        'client_display',
        'partner_display',
        'item_count_display',
    ]
    
    fieldsets = (
        ('Informations de commande', {
            'fields': (
                'order_number',
                'pickup_code',
                'status',
                ('total_amount_display', 'item_count_display'),
            )
        }),
        ('Relations', {
            'fields': (
                'client',
                'partner',
                'client_display',
                'partner_display',
            )
        }),
        ('Notes', {
            'fields': ('notes', 'cancellation_reason'),
            'classes': ('wide',),
        }),
        ('Timestamps', {
            'fields': (
                ('created_at', 'updated_at'),
                ('confirmed_at', 'picked_up_at', 'cancelled_at')
            ),
            'classes': ('collapse',),
        }),
    )
    
    inlines = [OrderItemInline]
    
    actions = ['mark_as_confirmed', 'mark_as_ready', 'mark_as_picked_up', 'mark_as_cancelled']
    
    list_per_page = 25
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'client', 
                'partner', 
                'status',
                'notes',
            ),
        }),
    )
    
    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)
    
    def get_readonly_fields(self, request, obj=None):
        if not obj:
            return ['order_number', 'pickup_code']
        return self.readonly_fields
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'client', 'partner'
        ).prefetch_related('items')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.total_amount = 0
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """Sauvegarde le formset et met à jour le total"""
        instances = formset.save(commit=False)
        
        # Supprimer les objets marqués pour suppression
        for obj in formset.deleted_objects:
            obj.delete()
        
        # Sauvegarder les nouvelles instances
        for instance in instances:
            # S'assurer que unit_price est défini
            if instance.offer and not instance.unit_price:
                instance.unit_price = instance.offer.discounted_price
            instance.save()
        
        formset.save_m2m()
        
        # Recalculer le total
        if form.instance.pk:
            total = sum(item.subtotal for item in form.instance.items.all())
            form.instance.total_amount = total
            form.instance.save(update_fields=['total_amount'])
    
    def client_link(self, obj):
        if obj.client:
            url = reverse('admin:accounts_user_change', args=[obj.client.id])
            return format_html('<a href="{}">{}</a>', url, obj.client.get_full_name() or obj.client.email)
        return "-"
    client_link.short_description = 'Client'
    
    def partner_link(self, obj):
        if obj.partner:
            url = reverse('admin:partners_partner_change', args=[obj.partner.id])
            return format_html('<a href="{}">{}</a>', url, obj.partner.name)
        return "-"
    partner_link.short_description = 'Partenaire'
    
    def client_display(self, obj):
        if obj and obj.client:
            url = reverse('admin:accounts_user_change', args=[obj.client.id])
            return format_html('<a href="{}">{}</a>', url, obj.client.get_full_name() or obj.client.email)
        return "-"
    client_display.short_description = 'Client'
    
    def partner_display(self, obj):
        if obj and obj.partner:
            url = reverse('admin:partners_partner_change', args=[obj.partner.id])
            return format_html('<a href="{}">{}</a>', url, obj.partner.name)
        return "-"
    partner_display.short_description = 'Partenaire'
    
    def status_colored(self, obj):
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'blue',
            'READY': 'green',
            'PICKED_UP': 'gray',
            'CANCELLED': 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_colored.short_description = 'Statut'
    
    def total_amount_display(self, obj):
        if obj and obj.total_amount is not None:
            color = 'green' if obj.total_amount > 0 else 'gray'
            return format_html(
                '<strong style="color: {};">{}</strong>',
                color,
                obj.total_amount
            )
        return format_html('<span style="color: gray;">0</span>')
    total_amount_display.short_description = 'Montant total'
    
    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Articles'
    
    def item_count_display(self, obj):
        count = obj.items.count()
        if count > 0:
            return format_html('<strong>{}</strong> article(s)', count)
        return format_html('<span style="color: orange;">Aucun article</span>')
    item_count_display.short_description = 'Articles'
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    # Actions
    def mark_as_confirmed(self, request, queryset):
        updated = queryset.exclude(status=Order.Status.CONFIRMED).update(
            status=Order.Status.CONFIRMED,
            confirmed_at=timezone.now()
        )
        self.message_user(request, f"{updated} commande(s) confirmée(s).")
    mark_as_confirmed.short_description = "Confirmer"
    
    def mark_as_ready(self, request, queryset):
        updated = queryset.exclude(status=Order.Status.READY).update(
            status=Order.Status.READY
        )
        self.message_user(request, f"{updated} commande(s) prête(s).")
    mark_as_ready.short_description = "Marquer comme prête"
    
    def mark_as_picked_up(self, request, queryset):
        empty_orders = [str(obj) for obj in queryset if obj.items.count() == 0]
        if empty_orders:
            self.message_user(
                request, 
                f"Commandes sans articles : {', '.join(empty_orders)}",
                level='ERROR'
            )
            return
        
        updated = queryset.exclude(status=Order.Status.PICKED_UP).update(
            status=Order.Status.PICKED_UP,
            picked_up_at=timezone.now()
        )
        self.message_user(request, f"{updated} commande(s) retirée(s).")
    mark_as_picked_up.short_description = "Marquer comme retirée"
    
    def mark_as_cancelled(self, request, queryset):
        if 'apply' in request.POST:
            reason = request.POST.get('cancellation_reason', 'Annulé par administrateur')
            updated = queryset.exclude(status=Order.Status.CANCELLED).update(
                status=Order.Status.CANCELLED,
                cancelled_at=timezone.now(),
                cancellation_reason=reason
            )
            self.message_user(request, f"{updated} commande(s) annulée(s).")
            return
        
        context = {
            'title': 'Annuler les commandes sélectionnées',
            'queryset': queryset,
            'action': 'mark_as_cancelled',
            'cancellation_reason': '',
        }
        return self.render_cancellation_form(request, context)
    mark_as_cancelled.short_description = "Annuler"
    
    def render_cancellation_form(self, request, context):
        from django.template.response import TemplateResponse
        return TemplateResponse(
            request,
            'admin/orders/cancel_confirmation.html',
            context
        )


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Administration des articles de commande"""
    
    list_display = [
        'id',
        'order_link',
        'offer_link',
        'quantity',
        'unit_price',
        'subtotal_display',
        'created_at'
    ]
    
    list_filter = ['created_at']
    
    search_fields = [
        'order__order_number',
        'offer__title'
    ]
    
    readonly_fields = ['subtotal_display', 'created_at', 'unit_price']
    
    fieldsets = (
        ('Informations', {
            'fields': (
                'order',
                'offer',
                'quantity',
                ('unit_price', 'subtotal_display'),
            )
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('order', 'offer')
    
    def order_link(self, obj):
        if obj.order:
            url = reverse('admin:orders_order_change', args=[obj.order.id])
            return format_html('<a href="{}">{}</a>', url, obj.order.order_number)
        return "-"
    order_link.short_description = 'Commande'
    
    def offer_link(self, obj):
        if obj.offer:
            url = reverse('admin:offers_foodoffer_change', args=[obj.offer.id])
            return format_html('<a href="{}">{}</a>', url, obj.offer.title[:50])
        return "-"
    offer_link.short_description = 'Offre'
    
    def subtotal_display(self, obj):
        if obj.pk:
            return format_html('<strong>{}</strong>', obj.subtotal)
        return "-"
    subtotal_display.short_description = 'Sous-total'
    
    def save_model(self, request, obj, form, change):
        # S'assurer que unit_price est défini
        if obj.offer and not obj.unit_price:
            obj.unit_price = obj.offer.discounted_price
        
        super().save_model(request, obj, form, change)
        
        # Mettre à jour le total de la commande
        if obj.order:
            total = sum(item.subtotal for item in obj.order.items.all())
            obj.order.total_amount = total
            obj.order.save(update_fields=['total_amount'])
    
    def delete_model(self, request, obj):
        order = obj.order
        super().delete_model(request, obj)
        
        if order:
            total = sum(item.subtotal for item in order.items.all()) if order.items.exists() else 0
            order.total_amount = total
            order.save(update_fields=['total_amount'])
    
    def has_add_permission(self, request):
        return True
    
    def has_delete_permission(self, request, obj=None):
        return True