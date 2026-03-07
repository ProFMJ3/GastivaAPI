from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Avg, Count
from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Administration des avis avec statistiques.
    """
    list_display = ['client_name', 'partner_name', 'rating_stars', 'comment_preview', 'created_at']
    list_filter = ['rating', 'is_visible', 'created_at']
    search_fields = ['client__email', 'comment']
    ordering = ['-created_at']
    
    def changelist_view(self, request, extra_context=None):
        """Ajoute des statistiques en haut de la liste."""
        response = super().changelist_view(request, extra_context)
        
        try:
            qs = self.get_queryset(request)
            
            stats = {
                'total': qs.count(),
                'avg_rating': qs.aggregate(avg=Avg('rating'))['avg'] or 0,
                'by_rating': {
                    '5★': qs.filter(rating=5).count(),
                    '4★': qs.filter(rating=4).count(),
                    '3★': qs.filter(rating=3).count(),
                    '2★': qs.filter(rating=2).count(),
                    '1★': qs.filter(rating=1).count(),
                }
            }
            
            response.context_data['stats'] = stats
        except:
            pass
            
        return response
    
    def client_name(self, obj):
        return obj.client.get_full_name() or obj.client.email
    client_name.short_description = 'Client'
    
    def partner_name(self, obj):
        return obj.order.partner.name if obj.order and obj.order.partner else '-'
    partner_name.short_description = 'Partenaire'
    
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html('<span style="color: #f5b342;">{}</span>', stars)
    rating_stars.short_description = 'Note'
    
    def comment_preview(self, obj):
        if not obj.comment:
            return '-'
        return obj.comment[:75] + ('...' if len(obj.comment) > 75 else '')
    comment_preview.short_description = 'Commentaire'