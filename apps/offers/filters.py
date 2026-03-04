import django_filters
from django.db import models
from django.utils import timezone
from .models import FoodOffer, FoodCategory


class FoodOfferFilter(django_filters.FilterSet):
    """
    Advanced filters for food offers.
    """
    # Basic filters
    category = django_filters.ModelChoiceFilter(queryset=FoodCategory.objects.filter(is_active=True))
    partner = django_filters.NumberFilter(field_name='partner__id')
    quarter = django_filters.CharFilter(field_name='partner__quarter', lookup_expr='icontains')
    
    # Price filters
    min_price = django_filters.NumberFilter(field_name='discounted_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='discounted_price', lookup_expr='lte')
    
    # Availability filters
    is_available = django_filters.BooleanFilter(method='filter_is_available')
    is_featured = django_filters.BooleanFilter()
    
    # Date filters
    pickup_before = django_filters.DateTimeFilter(field_name='pickup_deadline', lookup_expr='lte')
    pickup_after = django_filters.DateTimeFilter(field_name='pickup_deadline', lookup_expr='gte')
    
    # Status filters
    status = django_filters.MultipleChoiceFilter(choices=FoodOffer.Status.choices)

    class Meta:
        model = FoodOffer
        fields = ['category', 'partner', 'status', 'is_featured']

    def filter_is_available(self, queryset, name, value):
        """Filter available offers."""
        now = timezone.now()
        if value:
            return queryset.filter(
                status=FoodOffer.Status.ACTIVE,
                quantity_available__gt=models.F('quantity_reserved'),
                pickup_deadline__gt=now,
                available_from__lte=now
            )
        else:
            return queryset.exclude(
                status=FoodOffer.Status.ACTIVE,
                quantity_available__gt=models.F('quantity_reserved'),
                pickup_deadline__gt=now,
                available_from__lte=now
            )
        



class HomeOffersFilter(django_filters.FilterSet):
    """
    Filtres spécifiques pour la page d'accueil.
    """
    # Filtres de recherche
    search = django_filters.CharFilter(method='filter_search')
    
    # Filtres de catégorie
    category = django_filters.NumberFilter(field_name='category_id')
    category_slug = django_filters.CharFilter(field_name='category__slug')
    partner_category = django_filters.CharFilter(field_name='partner__category__slug')
    
    # Filtres de prix
    min_price = django_filters.NumberFilter(field_name='discounted_price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='discounted_price', lookup_expr='lte')
    
    # Filtre urgent
    urgent = django_filters.BooleanFilter(method='filter_urgent')
    
    # Filtre quartier
    quarter = django_filters.CharFilter(field_name='partner__quarter', lookup_expr='icontains')

    class Meta:
        model = FoodOffer
        fields = []

    def filter_search(self, queryset, name, value):
        """Recherche multi-champs."""
        return queryset.filter(
            models.Q(title__icontains=value) |
            models.Q(description__icontains=value) |
            models.Q(partner__name__icontains=value)
        )

    def filter_urgent(self, queryset, name, value):
        """Filtre les offres urgentes (expirant bientôt)."""
        if value:
            hours = self.data.get('expiring_hours', 1)
            if isinstance(hours, str):
                try:
                    hours = int(hours)
                except ValueError:
                    hours = 1
            
            deadline = timezone.now() + timezone.timedelta(hours=hours)
            return queryset.filter(pickup_deadline__lte=deadline)
        return queryset