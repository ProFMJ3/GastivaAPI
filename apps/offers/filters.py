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