from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.utils import timezone
from .models import Payment
from apps.orders.models import Order
from apps.orders.serializers import OrderListSerializer


class PaymentSerializer(serializers.ModelSerializer):
    """
    Serializer de base pour les paiements.
    """
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    time_elapsed = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'transaction_id', 'amount', 'payment_method',
            'payment_method_display', 'status', 'status_display', 'phone_number',
            'details', 'paid_at', 'failed_reason', 'time_elapsed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'transaction_id', 'paid_at', 'created_at', 'updated_at']

    @extend_schema_field(serializers.CharField)
    def get_time_elapsed(self, obj):
        """Temps écoulé depuis la création."""
        if obj.created_at:
            delta = timezone.now() - obj.created_at
            if delta.days > 0:
                return f"{delta.days} jours"
            elif delta.seconds // 3600 > 0:
                return f"{delta.seconds // 3600} heures"
            else:
                return f"{delta.seconds // 60} minutes"
        return None


class PaymentListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des paiements.
    """
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    restaurant_name = serializers.CharField(source='order.restaurant.name', read_only=True)
    client_name = serializers.CharField(source='order.client.get_full_name', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    status_color = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'order', 'order_number', 'amount',
            'restaurant_name', 'client_name', 'payment_method', 'payment_method_display',
            'status', 'status_display', 'status_color', 'paid_at', 'created_at'
        ]

    @extend_schema_field(serializers.CharField)
    def get_status_color(self, obj):
        """Couleur pour l'affichage du statut."""
        colors = {
            'PENDING': 'orange',
            'SUCCESS': 'green',
            'FAILED': 'red'
        }
        return colors.get(obj.status, 'gray')


class PaymentDetailSerializer(serializers.ModelSerializer):
    """
    Serializer pour les détails d'un paiement.
    """
    order_details = serializers.SerializerMethodField()
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    can_retry = serializers.SerializerMethodField()
    can_refund = serializers.SerializerMethodField()

    class Meta:
        model = Payment
        fields = [
            'id', 'transaction_id', 'order_details', 'amount',
            'payment_method', 'payment_method_display', 'status', 'status_display',
            'phone_number', 'details', 'paid_at', 'failed_reason',
            'can_retry', 'can_refund', 'created_at', 'updated_at'
        ]

    @extend_schema_field(serializers.DictField)
    def get_order_details(self, obj):
        """Détails de la commande associée."""
        return {
            'id': obj.order.id,
            'order_number': obj.order.order_number,
            'restaurant': obj.order.restaurant.name,
            'client': obj.order.client.get_full_name(),
            'total_amount': float(obj.order.total_amount),
            'status': obj.order.status
        }

    @extend_schema_field(serializers.BooleanField)
    def get_can_retry(self, obj):
        """Vérifier si le paiement peut être réessayé."""
        return obj.status == 'FAILED' and obj.created_at > timezone.now() - timezone.timedelta(hours=24)

    @extend_schema_field(serializers.BooleanField)
    def get_can_refund(self, obj):
        """Vérifier si le paiement peut être remboursé."""
        return obj.status == 'SUCCESS' and obj.paid_at > timezone.now() - timezone.timedelta(days=7)


class PaymentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'un paiement.
    """
    class Meta:
        model = Payment
        fields = ['order', 'payment_method', 'phone_number']

    def validate(self, data):
        """Validation des données de paiement."""
        order = data['order']
        payment_method = data['payment_method']
        
        # Vérifier que la commande existe et est en attente
        if order.status != 'PENDING':
            raise serializers.ValidationError(
                f"Impossible de payer une commande avec le statut {order.status}."
            )
        
        # Vérifier que la commande n'a pas déjà un paiement
        if hasattr(order, 'payment'):
            raise serializers.ValidationError(
                "Cette commande a déjà un paiement associé."
            )
        
        # Vérifier le téléphone pour les paiements mobile money
        if payment_method in ['TMONEY', 'FLOOZ']:
            phone = data.get('phone_number')
            if not phone:
                raise serializers.ValidationError(
                    "Le numéro de téléphone est requis pour le paiement mobile money."
                )
            
            # Validation simple du format togolais
            if not phone.startswith(('90', '91', '92', '93', '70', '71', '79')):
                raise serializers.ValidationError(
                    "Le numéro de téléphone doit être un numéro togolais valide."
                )
        
        # Ajouter le montant de la commande
        data['amount'] = order.total_amount
        
        return data

    def create(self, validated_data):
        """Créer le paiement avec statut PENDING."""
        validated_data['status'] = Payment.Status.PENDING
        return super().create(validated_data)


class PaymentProcessSerializer(serializers.Serializer):
    """
    Serializer pour le traitement d'un paiement.
    """
    action = serializers.ChoiceField(choices=['process', 'simulate_success', 'simulate_failure'])
    otp = serializers.CharField(max_length=6, required=False, help_text="Code OTP pour la simulation")

    def validate(self, data):
        """Validation de l'action."""
        action = data.get('action')
        
        if action == 'process' and not data.get('otp'):
            raise serializers.ValidationError(
                "Le code OTP est requis pour traiter le paiement."
            )
        
        return data


class PaymentStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour du statut (admin).
    """
    class Meta:
        model = Payment
        fields = ['status', 'failed_reason']
        extra_kwargs = {
            'failed_reason': {'required': False}
        }

    def validate(self, data):
        """Valider le changement de statut."""
        new_status = data.get('status')
        instance = self.instance
        
        if instance and instance.status == 'SUCCESS' and new_status != 'SUCCESS':
            raise serializers.ValidationError(
                "Impossible de modifier un paiement réussi."
            )
        
        if new_status == 'FAILED' and not data.get('failed_reason'):
            data['failed_reason'] = 'Échec du paiement'
        
        return data

    def update(self, instance, validated_data):
        """Mettre à jour avec la date appropriée."""
        if validated_data.get('status') == 'SUCCESS' and instance.status != 'SUCCESS':
            validated_data['paid_at'] = timezone.now()
        return super().update(instance, validated_data)


class PaymentRefundSerializer(serializers.Serializer):
    """
    Serializer pour le remboursement.
    """
    reason = serializers.CharField(required=True, max_length=300)
    notify_client = serializers.BooleanField(default=True)


class PaymentStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques des paiements.
    """
    total_payments = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    successful_payments = serializers.IntegerField()
    successful_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    failed_payments = serializers.IntegerField()
    pending_payments = serializers.IntegerField()
    payment_method_breakdown = serializers.DictField()
    daily_stats = serializers.ListField(child=serializers.DictField())