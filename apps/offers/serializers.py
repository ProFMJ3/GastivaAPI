from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.utils import timezone
from django.db import models as django_models

from .models import FoodCategory, FoodOffer
from apps.partners.serializers import PartnerListSerializer
from apps.partners.models import Partner


class FoodCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for food categories.
    """
    offers_count = serializers.SerializerMethodField()

    class Meta:
        model = FoodCategory
        fields = ['id', 'name', 'slug', 'icon', 'description', 'is_active', 'offers_count']
        read_only_fields = ['id']

    @extend_schema_field(serializers.IntegerField)
    def get_offers_count(self, obj):
        """Number of active offers in this category."""
        return obj.offers.filter(status='ACTIVE').count()


class FoodCategoryDetailSerializer(serializers.ModelSerializer):
    """
    Detailed serializer for categories with offers list.
    """
    offers = serializers.SerializerMethodField()

    class Meta:
        model = FoodCategory
        fields = ['id', 'name', 'slug', 'icon', 'description', 'is_active', 'offers']

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_offers(self, obj):
        """Return active offers in this category."""
        from .serializers import FoodOfferListSerializer
        offers = obj.offers.filter(status='ACTIVE')[:10]
        return FoodOfferListSerializer(offers, many=True).data


class FoodOfferListSerializer(serializers.ModelSerializer):
    """
    Serializer for offer list (simplified view).
    """
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    partner_quarter = serializers.CharField(source='partner.quarter', read_only=True)
    partner_logo = serializers.ImageField(source='partner.logo', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    remaining_quantity = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    time_remaining = serializers.SerializerMethodField()

    class Meta:
        model = FoodOffer
        fields = [
            'id', 'title', 'partner', 'partner_name', 'partner_quarter', 'partner_logo',
            'category', 'category_name', 'image', 'original_price', 'discounted_price',
            'discount_percentage', 'quantity_available', 'remaining_quantity',
            'pickup_deadline', 'is_available', 'time_remaining', 'is_featured',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField)
    def get_time_remaining(self, obj):
        """Time remaining before expiry."""
        if obj.pickup_deadline and obj.pickup_deadline > timezone.now():
            delta = obj.pickup_deadline - timezone.now()
            if delta.days > 0:
                return f"{delta.days}j {delta.seconds//3600}h"
            elif delta.seconds//3600 > 0:
                return f"{delta.seconds//3600}h {(delta.seconds//60)%60}min"
            else:
                return f"{delta.seconds//60}min"
        return "Expired"


class FoodOfferDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for offer details (full view).
    """
    partner = PartnerListSerializer(read_only=True)
    category = FoodCategorySerializer(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    remaining_quantity = serializers.IntegerField(read_only=True)
    is_available = serializers.BooleanField(read_only=True)
    time_remaining = serializers.SerializerMethodField()
    similar_offers = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = FoodOffer
        fields = [
            'id', 'title', 'description', 'partner', 'category',
            'image', 'original_price', 'discounted_price', 'discount_percentage',
            'quantity_available', 'quantity_reserved', 'remaining_quantity',
            'pickup_deadline', 'available_from', 'status', 'is_featured',
            'is_available', 'time_remaining', 'similar_offers',
            'can_edit', 'can_delete', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField)
    def get_time_remaining(self, obj):
        """Time remaining before expiry."""
        if obj.pickup_deadline and obj.pickup_deadline > timezone.now():
            delta = obj.pickup_deadline - timezone.now()
            if delta.days > 0:
                return f"{delta.days} days {delta.seconds//3600} hours"
            elif delta.seconds//3600 > 0:
                return f"{delta.seconds//3600} hours {(delta.seconds//60)%60} minutes"
            else:
                return f"{delta.seconds//60} minutes"
        return "Expired"

    @extend_schema_field(FoodOfferListSerializer(many=True))
    def get_similar_offers(self, obj):
        """Similar offers (same category or same partner)."""
        from .serializers import FoodOfferListSerializer
        similar = FoodOffer.objects.filter(
            status='ACTIVE'
        ).filter(
            django_models.Q(category=obj.category) | django_models.Q(partner=obj.partner)
        ).exclude(id=obj.id)[:3]
        return FoodOfferListSerializer(similar, many=True).data

    @extend_schema_field(serializers.BooleanField)
    def get_can_edit(self, obj):
        """Check if current user can edit this offer."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return request.user == obj.partner.owner or request.user.role == 'ADMIN'

    @extend_schema_field(serializers.BooleanField)
    def get_can_delete(self, obj):
        """Check if current user can delete this offer."""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return request.user == obj.partner.owner or request.user.role == 'ADMIN'


class FoodOfferCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating and updating offers.
    """
    class Meta:
        model = FoodOffer
        fields = [
            'title', 'description', 'category', 'image',
            'original_price', 'discounted_price',
            'quantity_available', 'pickup_deadline', 'available_from',
            'is_featured'
        ]

    def validate(self, data):
        """Custom validation."""
        # Check discounted price < original price
        if data['discounted_price'] >= data['original_price']:
            raise serializers.ValidationError(
                "Discounted price must be less than original price."
            )
        
        # Check pickup deadline > available from
        if data['pickup_deadline'] <= data['available_from']:
            raise serializers.ValidationError(
                "Pickup deadline must be after available from date."
            )
        
        # Check pickup deadline is in the future
        if data['pickup_deadline'] <= timezone.now():
            raise serializers.ValidationError(
                "Pickup deadline must be in the future."
            )
        
        return data

    def create(self, validated_data):
        """Create offer with partner from request."""
        user = self.context['request'].user
        
        # For a user with multiple partners, we need to specify which partner
        # This expects that the frontend sends a 'partner_id' or we use the first one
        partner_id = self.context['request'].data.get('partner_id')
        
        if partner_id:
            try:
                partner = Partner.objects.get(id=partner_id, owner=user)
            except Partner.DoesNotExist:
                raise serializers.ValidationError(
                    {"partner_id": "Partner not found or you don't own it."}
                )
        else:
            # If no partner_id, try to get the first partner
            partners = Partner.objects.filter(owner=user)
            if not partners.exists():
                raise serializers.ValidationError(
                    "You don't have any partner. Please create a partner first."
                )
            partner = partners.first()
        
        validated_data['partner'] = partner
        validated_data['status'] = FoodOffer.Status.ACTIVE
        return super().create(validated_data)


class FoodOfferStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for status update.
    """
    class Meta:
        model = FoodOffer
        fields = ['status']
        extra_kwargs = {
            'status': {'required': True}
        }


class FoodOfferReserveSerializer(serializers.Serializer):
    """
    Serializer for reserving an offer.
    """
    quantity = serializers.IntegerField(min_value=1, required=True)

    def validate_quantity(self, value):
        """Validate quantity."""
        if value <= 0:
            raise serializers.ValidationError("Quantity must be positive.")
        return value


class FoodOfferStatsSerializer(serializers.Serializer):
    """
    Serializer for offer statistics.
    """
    total_offers = serializers.IntegerField()
    active_offers = serializers.IntegerField()
    reserved_offers = serializers.IntegerField()
    expired_offers = serializers.IntegerField()
    total_reserved = serializers.IntegerField()
    average_discount = serializers.FloatField()
    most_popular_category = serializers.DictField(allow_null=True)