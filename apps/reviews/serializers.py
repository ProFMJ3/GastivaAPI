from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.utils import timezone
from django.db.models import Avg
from .models import Review
from apps.accounts.serializers import UserSerializer
from apps.partners.serializers import PartnerListSerializer


class ReviewSerializer(serializers.ModelSerializer):
    """
    Serializer de base pour les avis.
    """
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_avatar = serializers.ImageField(source='client.avatar', read_only=True)
    partner_name = serializers.SerializerMethodField()
    partner_id = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    rating_display = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'client', 'client_name', 'client_avatar', 
            'partner_id', 'partner_name', 'order', 'rating', 'rating_display',
            'comment', 'is_visible', 'time_ago', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'client_name', 'client_avatar', 'partner_id', 'partner_name',
                           'time_ago', 'created_at', 'updated_at']

    @extend_schema_field(serializers.IntegerField)
    def get_partner_id(self, obj):
        return obj.partner.id if obj.partner else None

    @extend_schema_field(serializers.CharField)
    def get_partner_name(self, obj):
        return obj.partner.name if obj.partner else None

    @extend_schema_field(serializers.CharField)
    def get_time_ago(self, obj):
        """Temps écoulé depuis la création."""
        delta = timezone.now() - obj.created_at
        if delta.days > 30:
            months = delta.days // 30
            return f"il y a {months} mois" if months > 1 else "il y a 1 mois"
        elif delta.days > 0:
            return f"il y a {delta.days} jours" if delta.days > 1 else "il y a 1 jour"
        elif delta.seconds // 3600 > 0:
            hours = delta.seconds // 3600
            return f"il y a {hours} heures" if hours > 1 else "il y a 1 heure"
        elif delta.seconds // 60 > 0:
            minutes = delta.seconds // 60
            return f"il y a {minutes} minutes" if minutes > 1 else "il y a 1 minute"
        else:
            return "à l'instant"

    @extend_schema_field(serializers.CharField)
    def get_rating_display(self, obj):
        """Affiche les étoiles."""
        return "★" * obj.rating + "☆" * (5 - obj.rating)


class ReviewListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des avis.
    """
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_avatar = serializers.ImageField(source='client.avatar', read_only=True)
    partner_name = serializers.SerializerMethodField()
    partner_quarter = serializers.SerializerMethodField()
    rating_display = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    comment_preview = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'client_name', 'client_avatar', 'partner_name',
            'partner_quarter', 'rating', 'rating_display', 'comment_preview',
            'time_ago', 'created_at'
        ]

    @extend_schema_field(serializers.CharField)
    def get_partner_name(self, obj):
        return obj.partner.name if obj.partner else None

    @extend_schema_field(serializers.CharField)
    def get_partner_quarter(self, obj):
        return obj.partner.quarter if obj.partner else None

    @extend_schema_field(serializers.CharField)
    def get_rating_display(self, obj):
        return "★" * obj.rating + "☆" * (5 - obj.rating)

    @extend_schema_field(serializers.CharField)
    def get_time_ago(self, obj):
        delta = timezone.now() - obj.created_at
        if delta.days > 0:
            return f"il y a {delta.days}j"
        elif delta.seconds // 3600 > 0:
            return f"il y a {delta.seconds // 3600}h"
        else:
            return f"il y a {delta.seconds // 60}min"

    @extend_schema_field(serializers.CharField)
    def get_comment_preview(self, obj):
        if obj.comment and len(obj.comment) > 50:
            return obj.comment[:50] + "..."
        return obj.comment


class ReviewDetailSerializer(serializers.ModelSerializer):
    """
    Serializer pour les détails d'un avis.
    """
    client_details = serializers.SerializerMethodField()
    partner_details = serializers.SerializerMethodField()
    order_details = serializers.SerializerMethodField()
    rating_display = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'client_details', 'partner_details', 'order_details',
            'rating', 'rating_display', 'comment', 'is_visible',
            'time_ago', 'created_at', 'updated_at',
            'can_edit', 'can_delete'
        ]

    @extend_schema_field(serializers.DictField)
    def get_client_details(self, obj):
        return {
            'id': obj.client.id,
            'name': obj.client.get_full_name(),
            'avatar': obj.client.avatar.url if obj.client.avatar else None,
            'total_reviews': obj.client.reviews.count()
        }

    @extend_schema_field(serializers.DictField)
    def get_partner_details(self, obj):
        if not obj.partner:
            return None
            
        # Calculer la note moyenne du partner
        from django.db.models import Avg
        reviews = Review.objects.filter(order__partner=obj.partner, is_visible=True)
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        return {
            'id': obj.partner.id,
            'name': obj.partner.name,
            'quarter': obj.partner.quarter,
            'phone': obj.partner.phone,
            'average_rating': round(avg_rating, 1),
            'total_reviews': reviews.count()
        }

    @extend_schema_field(serializers.DictField)
    def get_order_details(self, obj):
        if obj.order:
            return {
                'id': obj.order.id,
                'order_number': obj.order.order_number,
                'total_amount': float(obj.order.total_amount),
                'items': [
                    {
                        'title': item.offer.title,
                        'quantity': item.quantity
                    }
                    for item in obj.order.items.all()[:3]
                ]
            }
        return None

    @extend_schema_field(serializers.CharField)
    def get_rating_display(self, obj):
        return "★" * obj.rating + "☆" * (5 - obj.rating)

    @extend_schema_field(serializers.CharField)
    def get_time_ago(self, obj):
        delta = timezone.now() - obj.created_at
        if delta.days > 30:
            months = delta.days // 30
            return f"il y a {months} mois"
        elif delta.days > 0:
            return f"il y a {delta.days} jours"
        elif delta.seconds // 3600 > 0:
            return f"il y a {delta.seconds // 3600} heures"
        else:
            return f"il y a {delta.seconds // 60} minutes"

    @extend_schema_field(serializers.BooleanField)
    def get_can_edit(self, obj):
        """Vérifier si l'utilisateur peut modifier l'avis."""
        user = self.context.get('request').user
        return user == obj.client and obj.created_at > timezone.now() - timezone.timedelta(days=7)

    @extend_schema_field(serializers.BooleanField)
    def get_can_delete(self, obj):
        """Vérifier si l'utilisateur peut supprimer l'avis."""
        user = self.context.get('request').user
        return user == obj.client or user.role == 'ADMIN'


class ReviewCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'un avis.
    """
    class Meta:
        model = Review
        fields = ['order', 'rating', 'comment']  # Plus de champ partner

    def validate(self, data):
        """Validation des données."""
        user = self.context['request'].user
        order = data.get('order')
        
        # Vérifier que l'utilisateur est bien un client
        if user.role != 'CLIENT':
            raise serializers.ValidationError(
                "Seuls les clients peuvent laisser des avis."
            )
        
        # Vérifier que la commande appartient bien au client
        if order.client != user:
            raise serializers.ValidationError(
                "Vous ne pouvez évaluer que vos propres commandes."
            )
        
        # Vérifier que la commande est terminée
        if order.status != 'PICKED_UP':
            raise serializers.ValidationError(
                "Vous ne pouvez évaluer que les commandes terminées."
            )
        
        # Vérifier qu'il n'y a pas déjà un avis pour cette commande
        if hasattr(order, 'review'):
            raise serializers.ValidationError(
                "Un avis existe déjà pour cette commande."
            )
        
        return data

    def create(self, validated_data):
        """Créer l'avis avec le client connecté."""
        validated_data['client'] = self.context['request'].user
        return super().create(validated_data)


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour d'un avis.
    """
    class Meta:
        model = Review
        fields = ['rating', 'comment']

    def validate(self, data):
        """Vérifier que l'avis peut être modifié."""
        instance = self.instance
        if instance.created_at < timezone.now() - timezone.timedelta(days=7):
            raise serializers.ValidationError(
                "Les avis de plus de 7 jours ne peuvent plus être modifiés."
            )
        return data


class ReviewModerateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la modération des avis (admin).
    """
    class Meta:
        model = Review
        fields = ['is_visible']


class ReviewStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques des avis.
    """
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    rating_distribution = serializers.DictField()
    top_reviewers = serializers.ListField(child=serializers.DictField())
    recent_reviews = serializers.ListField(child=serializers.DictField())
    top_partners = serializers.ListField(child=serializers.DictField())


class PartnerReviewStatsSerializer(serializers.Serializer):
    """
    Statistiques des avis pour un partner.
    """
    partner_id = serializers.IntegerField()
    partner_name = serializers.CharField()
    total_reviews = serializers.IntegerField()
    average_rating = serializers.FloatField()
    rating_distribution = serializers.DictField()
    recent_reviews = ReviewListSerializer(many=True)