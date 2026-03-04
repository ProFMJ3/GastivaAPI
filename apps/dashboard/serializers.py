from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.utils import timezone
from datetime import timedelta
from apps.offers.models import FoodOffer
from apps.orders.models import Order
from apps.reviews.models import Review
from apps.partners.models import Partner


class PartnerStatsOverviewSerializer(serializers.Serializer):
    """
    Aperçu général des statistiques du partenaire.
    """
    # Statistiques des offres
    total_offers = serializers.IntegerField()
    active_offers = serializers.IntegerField()
    reserved_offers = serializers.IntegerField()
    expired_offers = serializers.IntegerField()
    sold_out_offers = serializers.IntegerField()
    
    # Statistiques des commandes
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    confirmed_orders = serializers.IntegerField()
    ready_orders = serializers.IntegerField()
    completed_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    
    # Statistiques financières
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    today_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    week_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    month_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=8, decimal_places=2)
    
    # Statistiques des avis
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    rating_distribution = serializers.DictField(child=serializers.IntegerField())
    
    # Impact environnemental
    total_food_saved_kg = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_meals_saved = serializers.IntegerField()
    total_co2_saved_kg = serializers.DecimalField(max_digits=10, decimal_places=2)


class PartnerRevenueChartSerializer(serializers.Serializer):
    """
    Données pour le graphique des revenus.
    """
    labels = serializers.ListField(child=serializers.CharField())
    datasets = serializers.ListField(child=serializers.DictField())


class PartnerTopOffersSerializer(serializers.Serializer):
    """
    Top des offres les plus vendues.
    """
    offer_id = serializers.IntegerField()
    offer_title = serializers.CharField()
    total_quantity = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    orders_count = serializers.IntegerField()


class PartnerRecentActivitySerializer(serializers.Serializer):
    """
    Activités récentes du partenaire.
    """
    id = serializers.IntegerField()
    type = serializers.CharField()  # 'order', 'offer', 'review'
    title = serializers.CharField()
    description = serializers.CharField()
    time_ago = serializers.CharField()
    status = serializers.CharField(allow_null=True)
    link = serializers.CharField()


class PartnerOfferStatsSerializer(serializers.ModelSerializer):
    """
    Statistiques détaillées pour chaque offre.
    """
    total_orders = serializers.IntegerField()
    total_quantity_sold = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    conversion_rate = serializers.FloatField()  # (quantité vendue / quantité disponible) * 100
    time_remaining = serializers.CharField()
    performance = serializers.CharField()  # 'good', 'average', 'poor'

    class Meta:
        model = FoodOffer
        fields = [
            'id', 'title', 'discounted_price', 'original_price',
            'quantity_available', 'quantity_reserved', 'quantity_sold',
            'status', 'pickup_deadline', 'created_at',
            'total_orders', 'total_quantity_sold', 'total_revenue',
            'conversion_rate', 'time_remaining', 'performance'
        ]


class PartnerDashboardSerializer(serializers.Serializer):
    """
    Serializer principal pour le dashboard partenaire.
    """
    partner_info = serializers.DictField()
    overview = PartnerStatsOverviewSerializer()
    revenue_chart = PartnerRevenueChartSerializer()
    top_offers = PartnerTopOffersSerializer(many=True)
    recent_activity = PartnerRecentActivitySerializer(many=True)
    offers_stats = PartnerOfferStatsSerializer(many=True)