from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.utils import timezone
from .models import Order, OrderItem
from apps.offers.models import FoodOffer
from apps.offers.serializers import FoodOfferListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Serializer pour les articles de commande.
    """
    offer_title = serializers.CharField(source='offer.title', read_only=True)
    offer_image = serializers.ImageField(source='offer.image', read_only=True)
    partner_name = serializers.CharField(source='offer.partner.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id', 'offer', 'offer_title', 'offer_image', 'partner_name',
            'quantity', 'unit_price', 'subtotal', 'created_at'
        ]
        read_only_fields = ['id', 'subtotal', 'created_at']


class OrderItemCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'articles de commande.
    """
    class Meta:
        model = OrderItem
        fields = ['offer', 'quantity']

    def validate(self, data):
        """Vérifier la disponibilité de l'offre."""
        offer = data['offer']
        quantity = data['quantity']
        
        if not offer.is_available:
            raise serializers.ValidationError(
                f"L'offre '{offer.title}' n'est plus disponible."
            )
        
        if quantity > offer.remaining_quantity:
            raise serializers.ValidationError(
                f"Quantité demandée ({quantity}) supérieure à la disponibilité ({offer.remaining_quantity})"
            )
        
        return data


class OrderListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des commandes.
    """
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone_number', read_only=True)
    partner_name = serializers.CharField(source='partner.name', read_only=True)
    partner_quarter = serializers.CharField(source='partner.quarter', read_only=True)
    items_count = serializers.SerializerMethodField()
    time_remaining = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'client_name', 'client_phone',
            'partner_name', 'partner_quarter', 'status', 'status_display',
            'total_amount', 'pickup_code', 'items_count', 'time_remaining',
            'created_at', 'confirmed_at', 'picked_up_at'
        ]
        read_only_fields = ['id', 'order_number', 'pickup_code', 'created_at']

    @extend_schema_field(serializers.IntegerField)
    def get_items_count(self, obj):
        return obj.items.count()

    @extend_schema_field(serializers.CharField)
    def get_time_remaining(self, obj):
        """Temps restant avant confirmation (simulé)."""
        if obj.status == 'PENDING' and obj.created_at:
            elapsed = timezone.now() - obj.created_at
            remaining = max(0, 15 - elapsed.seconds // 60)  # 15 minutes pour payer
            return f"{remaining} minutes"
        return None


class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Serializer pour les détails d'une commande.
    """
    client_details = serializers.SerializerMethodField()
    partner_details = serializers.SerializerMethodField()
    items = OrderItemSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    time_remaining = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()
    can_confirm = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'client_details', 'partner_details',
            'status', 'status_display', 'total_amount', 'pickup_code', 'notes',
            'items', 'confirmed_at', 'picked_up_at', 'cancelled_at',
            'cancellation_reason', 'created_at', 'updated_at',
            'time_remaining', 'can_cancel', 'can_confirm'
        ]
        read_only_fields = ['id', 'order_number', 'pickup_code', 'created_at', 'updated_at']

    @extend_schema_field(serializers.DictField)
    def get_client_details(self, obj):
        return {
            'id': obj.client.id,
            'name': obj.client.get_full_name(),
            'phone': obj.client.phone_number,
            'email': obj.client.email
        }

    @extend_schema_field(serializers.DictField)
    def get_partner_details(self, obj):
        return {
            'id': obj.partner.id,
            'name': obj.partner.name,
            'phone': obj.partner.phone,
            'quarter': obj.partner.quarter,
            'address': obj.partner.address
        }

    @extend_schema_field(serializers.CharField)
    def get_time_remaining(self, obj):
        """Temps restant avant expiration pour les commandes en attente."""
        if obj.status == 'PENDING' and obj.created_at:
            elapsed = timezone.now() - obj.created_at
            remaining_seconds = max(0, 15 * 60 - elapsed.seconds)  # 15 minutes
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return None

    @extend_schema_field(serializers.BooleanField)
    def get_can_cancel(self, obj):
        """Vérifier si la commande peut être annulée."""
        return obj.status in ['PENDING', 'CONFIRMED']

    @extend_schema_field(serializers.BooleanField)
    def get_can_confirm(self, obj):
        """Vérifier si la commande peut être confirmée (pour le partner)."""
        return obj.status == 'PENDING'


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'une commande.
    """
    items = OrderItemCreateSerializer(many=True)
    
    # Champs en lecture seule qui seront retournés après création
    order_number = serializers.CharField(read_only=True)
    pickup_code = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = ['order_number', 'pickup_code', 'status', 'created_at', 'notes', 'items']

    def validate_items(self, value):
        """Valider qu'il y a au moins un article."""
        if not value:
            raise serializers.ValidationError("Au moins un article est requis.")
        return value

    def validate(self, data):
        """Validation globale."""
        items = data.get('items', [])
        
        if not items:
            return data
        
        # Vérifier que tous les articles sont du même partner
        first_offer = items[0]['offer']
        partner = first_offer.partner
        
        # Vérifications de disponibilité
        total_amount = 0
        items_details = []
        
        for item in items:
            offer = item['offer']
            quantity = item['quantity']
            
            # Vérifier que l'offre est disponible
            if not offer.is_available:
                raise serializers.ValidationError(
                    f"L'offre '{offer.title}' n'est plus disponible."
                )
            
            # Vérifier la quantité disponible
            if quantity > offer.remaining_quantity:
                raise serializers.ValidationError(
                    f"L'offre '{offer.title}' n'a que {offer.remaining_quantity} disponible(s)."
                )
            
            # Vérifier que tous les articles sont du même partner
            if item['offer'].partner != partner:
                raise serializers.ValidationError(
                    "Tous les articles doivent provenir du même partner."
                )
            
            total_amount += offer.discounted_price * quantity
            items_details.append({
                'offer': offer,
                'quantity': quantity,
                'unit_price': offer.discounted_price
            })
        
        data['partner'] = partner
        data['total_amount'] = total_amount
        data['items_details'] = items_details
        
        return data

    def create(self, validated_data):
        """Créer la commande et ses articles."""
        items_details = validated_data.pop('items_details')
        validated_data.pop('items')  # Retirer les items bruts
        
        validated_data['client'] = self.context['request'].user
        validated_data['partner'] = validated_data.pop('partner')
        validated_data['total_amount'] = validated_data.pop('total_amount')
        validated_data['status'] = Order.Status.PENDING
        
        # Créer la commande (le numéro et code sont générés automatiquement dans save)
        order = Order.objects.create(**validated_data)
        
        # Créer les articles et réserver les quantités
        for item_data in items_details:
            offer = item_data['offer']
            quantity = item_data['quantity']
            
            # Réserver la quantité (maintenant la méthode existe)
            offer.reserve(quantity)
            
            # Créer l'article
            OrderItem.objects.create(
                order=order,
                offer=offer,
                quantity=quantity,
                unit_price=offer.discounted_price
            )
        
        return order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la mise à jour du statut.
    """
    class Meta:
        model = Order
        fields = ['status', 'cancellation_reason']
        extra_kwargs = {
            'cancellation_reason': {'required': False}
        }

    def validate(self, data):
        """Valider le changement de statut."""
        order = self.instance
        new_status = data.get('status')
        
        # Vérifier les transitions valides
        valid_transitions = {
            'PENDING': ['CONFIRMED', 'CANCELLED'],
            'CONFIRMED': ['READY', 'CANCELLED'],
            'READY': ['PICKED_UP', 'CANCELLED'],
            'PICKED_UP': [],
            'CANCELLED': []
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            raise serializers.ValidationError(
                f"Transition de {order.status} vers {new_status} non autorisée."
            )
        
        # Raison d'annulation requise pour l'annulation
        if new_status == 'CANCELLED' and not data.get('cancellation_reason'):
            raise serializers.ValidationError(
                "Une raison d'annulation est requise."
            )
        
        return data

    def update(self, instance, validated_data):
        """Mettre à jour le statut avec la date correspondante."""
        new_status = validated_data.get('status')
        
        # Mettre à jour les timestamps selon le statut
        if new_status == 'CONFIRMED':
            instance.confirmed_at = timezone.now()
        elif new_status == 'PICKED_UP':
            instance.picked_up_at = timezone.now()
        elif new_status == 'CANCELLED':
            instance.cancelled_at = timezone.now()
            
            # Libérer les réservations
            for item in instance.items.all():
                item.offer.release_reservation(item.quantity)
        
        return super().update(instance, validated_data)


class OrderStatsSerializer(serializers.Serializer):
    """
    Serializer pour les statistiques des commandes.
    """
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    confirmed_orders = serializers.IntegerField()
    ready_orders = serializers.IntegerField()
    picked_up_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=8, decimal_places=2)
    most_ordered_items = serializers.ListField(child=serializers.DictField())