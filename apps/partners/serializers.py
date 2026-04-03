from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.utils import timezone
from django.db.models import Avg
from .models import CategoryPartner, Partner


class CategoryPartnerSerializer(serializers.ModelSerializer):
    partners_count = serializers.SerializerMethodField()

    class Meta:
        model = CategoryPartner
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'image',
            'is_active', 'display_order', 'partners_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    @extend_schema_field(serializers.IntegerField)
    def get_partners_count(self, obj):
        return obj.partners.filter(status='APPROVED').count()


class CategoryPartnerDetailSerializer(serializers.ModelSerializer):
    partners = serializers.SerializerMethodField()

    class Meta:
        model = CategoryPartner
        fields = [
            'id', 'name', 'slug', 'description', 'icon', 'image',
            'is_active', 'display_order', 'partners', 'created_at'
        ]

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_partners(self, obj):
        partners = obj.partners.filter(status='APPROVED')[:10]
        return PartnerListSerializer(partners, many=True).data


class PartnerListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    working_days_summary = serializers.SerializerMethodField()
    is_open_now = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'logo', 'cover_image', 'category', 'category_name',
            'category_icon', 'quarter', 'city', 'phone', 'status',
            'working_days_summary', 'is_open_now', 'owner_name', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']

    @extend_schema_field(serializers.CharField)
    def get_working_days_summary(self, obj):
        return obj.get_working_days_string()

    @extend_schema_field(serializers.BooleanField)
    def get_is_open_now(self, obj):
        return obj.is_open_now()

    @extend_schema_field(serializers.CharField)
    def get_owner_name(self, obj):
        return obj.owner.get_full_name()


class PartnerDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_details = CategoryPartnerSerializer(source='category', read_only=True)
    working_days_display = serializers.SerializerMethodField()
    working_days_summary = serializers.SerializerMethodField()
    is_open_now = serializers.SerializerMethodField()
    owner_details = serializers.SerializerMethodField()
    active_offers = serializers.SerializerMethodField()
    offers_count = serializers.SerializerMethodField()
    reviews_summary = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'description', 'logo', 'cover_image',
            'category', 'category_name', 'category_details',
            'address', 'city', 'quarter',
            'latitude', 'longitude', 'phone', 'email', 'website',
            'status', 'opening_time', 'closing_time', 'working_days',
            'working_days_display', 'working_days_summary',
            'is_open_now', 'owner_details',
            'active_offers', 'offers_count', 'reviews_summary',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']

    @extend_schema_field(serializers.ListField)
    def get_working_days_display(self, obj):
        try:
            return obj.get_working_days_display()
        except Exception:
            return []

    @extend_schema_field(serializers.CharField)
    def get_working_days_summary(self, obj):
        try:
            return obj.get_working_days_string()
        except Exception:
            return ''

    @extend_schema_field(serializers.BooleanField)
    def get_is_open_now(self, obj):
        try:
            return obj.is_open_now()
        except Exception:
            return False

    @extend_schema_field(serializers.DictField)
    def get_owner_details(self, obj):
        try:
            return {
                'id': obj.owner.id,
                'name': obj.owner.get_full_name(),
                'phone': getattr(obj.owner, 'phone_number', ''),
                'email': obj.owner.email,
                'total_partners': obj.owner.partners.count()
            }
        except Exception:
            return {'id': None, 'name': '', 'phone': '', 'email': '', 'total_partners': 0}

    @extend_schema_field(serializers.ListField)
    def get_active_offers(self, obj):
        try:
            from apps.offers.serializers import FoodOfferListSerializer
            active_offers = obj.food_offers.filter(status='ACTIVE')[:5]
            return FoodOfferListSerializer(
                active_offers, many=True,
                context=self.context
            ).data
        except Exception:
            return []

    @extend_schema_field(serializers.IntegerField)
    def get_offers_count(self, obj):
        try:
            return obj.food_offers.filter(status='ACTIVE').count()
        except Exception:
            return 0

    @extend_schema_field(serializers.DictField)
    def get_reviews_summary(self, obj):
        """Summary of partner reviews — FIX: utiliser order__partner."""
        try:
            from apps.reviews.models import Review
            # ✅ Fix: filtrer par order__partner au lieu de order__offer__partner
            reviews = Review.objects.filter(
                order__partner=obj,
                is_visible=True
            )
            total = reviews.count()
            avg = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
            return {
                'total_reviews': total,
                'average_rating': round(float(avg), 1),
                'rating_distribution': {
                    str(i): reviews.filter(rating=i).count()
                    for i in range(1, 6)
                }
            }
        except Exception:
            return {
                'total_reviews': 0,
                'average_rating': 0,
                'rating_distribution': {}
            }


class PartnerCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = [
            'name', 'description', 'category', 'logo', 'cover_image',
            'address', 'city', 'quarter', 'latitude', 'longitude',
            'phone', 'email', 'website', 'opening_time', 'closing_time',
            'working_days'
        ]

    def validate_working_days(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one working day is required.")
        valid_days = [day[0] for day in Partner.DAYS_OF_WEEK]
        for day in value:
            if day not in valid_days:
                raise serializers.ValidationError(
                    f"'{day}' is not a valid day. Choose from {valid_days}")
        return value

    def validate(self, data):
        if data.get('opening_time') and data.get('closing_time'):
            if data['opening_time'] >= data['closing_time']:
                raise serializers.ValidationError(
                    "Opening time must be before closing time.")
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        validated_data['status'] = Partner.Status.PENDING
        return super().create(validated_data)


class PartnerStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partner
        fields = ['status']


class PartnerGeoSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_open_now = serializers.SerializerMethodField()

    class Meta:
        model = Partner
        fields = [
            'id', 'name', 'category', 'category_name', 'quarter',
            'latitude', 'longitude', 'is_open_now'
        ]

    @extend_schema_field(serializers.BooleanField)
    def get_is_open_now(self, obj):
        return obj.is_open_now()