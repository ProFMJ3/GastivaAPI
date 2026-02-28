import django_filters
from django.db import models
from .models import Partner


class PartnerFilter(django_filters.FilterSet):
    """
    Advanced filters for partners.
    """
    category = django_filters.NumberFilter(field_name='category__id')
    quarter = django_filters.CharFilter(lookup_expr='icontains')
    city = django_filters.CharFilter(lookup_expr='icontains')
    status = django_filters.ChoiceFilter(choices=Partner.Status.choices)
    
    # Filter for partners open now
    open_now = django_filters.BooleanFilter(method='filter_open_now')
    
    # Filter by opening day
    open_on = django_filters.CharFilter(method='filter_open_on')

    class Meta:
        model = Partner
        fields = ['category', 'quarter', 'city', 'status']

    def filter_open_now(self, queryset, name, value):
        """Filter partners open at current time."""
        if value:
            open_ids = []
            for partner in queryset:
                if partner.is_open_now():
                    open_ids.append(partner.id)
            return queryset.filter(id__in=open_ids)
        return queryset

    def filter_open_on(self, queryset, name, value):
        """Filter partners open on a specific day."""
        valid_days = [day[0] for day in Partner.DAYS_OF_WEEK]
        if value in valid_days:
            return queryset.filter(working_days__contains=[value])
        return queryset.none()