from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.utils import timezone
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer de base pour les notifications.
    """
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'notification_type', 'type_display',
            'priority', 'priority_display', 'title', 'message', 'data',
            'image', 'icon', 'is_read', 'read_at', 'time_ago',
            'is_expired', 'created_at'
        ]
        read_only_fields = ['id', 'recipient', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField)
    def get_time_ago(self, obj):
        return obj.time_ago


class NotificationDetailSerializer(serializers.ModelSerializer):
    """
    Serializer détaillé pour les notifications avec objet lié.
    """
    recipient_name = serializers.CharField(source='recipient.get_full_name', read_only=True)
    recipient_avatar = serializers.ImageField(source='recipient.avatar', read_only=True)
    type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    time_ago = serializers.SerializerMethodField()
    is_expired = serializers.BooleanField(read_only=True)
    related_object_type = serializers.SerializerMethodField()
    related_object_data = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            'id', 'recipient', 'recipient_name', 'recipient_avatar',
            'notification_type', 'type_display', 'priority', 'priority_display',
            'title', 'message', 'data', 'image', 'icon',
            'is_read', 'read_at', 'time_ago', 'is_expired',
            'related_object_type', 'related_object_data',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'recipient', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField)
    def get_time_ago(self, obj):
        return obj.time_ago

    @extend_schema_field(serializers.CharField)
    def get_related_object_type(self, obj):
        """Retourne le type de l'objet lié."""
        if obj.content_type:
            return obj.content_type.model
        return None

    @extend_schema_field(serializers.DictField)
    def get_related_object_data(self, obj):
        """Retourne les données de l'objet lié."""
        if not obj.related_object:
            return None
        
        # Retourner différentes données selon le type d'objet
        if hasattr(obj.related_object, 'order_number'):
            # C'est une commande
            return {
                'id': obj.related_object.id,
                'order_number': obj.related_object.order_number,
                'total_amount': str(obj.related_object.total_amount),
                'status': obj.related_object.status
            }
        elif hasattr(obj.related_object, 'title'):
            # C'est une offre
            return {
                'id': obj.related_object.id,
                'title': obj.related_object.title,
                'discounted_price': str(obj.related_object.discounted_price)
            }
        elif hasattr(obj.related_object, 'name'):
            # C'est un partenaire
            return {
                'id': obj.related_object.id,
                'name': obj.related_object.name,
                'quarter': obj.related_object.quarter
            }
        
        return {'id': obj.object_id}


class NotificationCreateSerializer(serializers.Serializer):
    """
    Serializer pour la création de notifications (admin uniquement).
    """
    recipient_id = serializers.IntegerField(required=True)
    notification_type = serializers.ChoiceField(choices=Notification.NotificationType.choices)
    priority = serializers.ChoiceField(choices=Notification.Priority.choices, default='MEDIUM')
    title = serializers.CharField(max_length=255)
    message = serializers.CharField()
    data = serializers.JSONField(default=dict, required=False)
    image = serializers.ImageField(required=False)
    icon = serializers.CharField(max_length=50, default='notifications')
    expires_in_days = serializers.IntegerField(default=30, min_value=1, max_value=365)

    def create(self, validated_data):
        from django.contrib.contenttypes.models import ContentType
        from apps.accounts.models import User

        try:
            recipient = User.objects.get(id=validated_data['recipient_id'])
        except User.DoesNotExist:
            raise serializers.ValidationError({"recipient_id": "Utilisateur non trouvé"})

        # Calculer la date d'expiration
        expires_at = timezone.now() + timezone.timedelta(days=validated_data.pop('expires_in_days'))

        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=validated_data['notification_type'],
            priority=validated_data['priority'],
            title=validated_data['title'],
            message=validated_data['message'],
            data=validated_data.get('data', {}),
            image=validated_data.get('image'),
            icon=validated_data.get('icon', 'notifications'),
            expires_at=expires_at
        )

        return notification


class NotificationMarkReadSerializer(serializers.Serializer):
    """
    Serializer pour marquer les notifications comme lues.
    """
    notification_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        help_text="Liste des IDs à marquer. Si vide, toutes les notifications sont marquées."
    )
    mark_all = serializers.BooleanField(default=False)


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    """
    Serializer pour les préférences de notification.
    """
    class Meta:
        model = NotificationPreference
        fields = [
            'allow_push', 'allow_email', 'allow_sms', 'allow_in_app',
            'type_preferences', 'quiet_hours_start', 'quiet_hours_end'
        ]

    def validate(self, data):
        """Valider les heures de silence."""
        start = data.get('quiet_hours_start')
        end = data.get('quiet_hours_end')
        
        if start and end and start >= end:
            raise serializers.ValidationError(
                "L'heure de début doit être antérieure à l'heure de fin."
            )
        
        return data


class NotificationStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques des notifications.
    """
    total_unread = serializers.IntegerField()
    total_notifications = serializers.IntegerField()
    notifications_by_type = serializers.DictField(child=serializers.IntegerField())
    notifications_by_priority = serializers.DictField(child=serializers.IntegerField())
    recent_activity = serializers.ListField(child=serializers.DictField())