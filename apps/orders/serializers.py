from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from django.utils import timezone
from .models import Order, OrderItem
from apps.offers.models import FoodOffer
from apps.offers.serializers import FoodOfferListSerializer


class OrderItemSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = OrderItem
        fields = ['offer', 'quantity']

    def validate(self, data):
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
    # ── Ajouts pour l'affichage image dans la liste ────────────
    first_item_title = serializers.SerializerMethodField()
    first_item_image = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'client_name', 'client_phone',
            'partner_name', 'partner_quarter', 'status', 'status_display',
            'total_amount', 'pickup_code', 'items_count',
            'first_item_title', 'first_item_image',
            'time_remaining', 'created_at', 'confirmed_at', 'picked_up_at'
        ]
        read_only_fields = ['id', 'order_number', 'pickup_code', 'created_at']

    @extend_schema_field(serializers.IntegerField)
    def get_items_count(self, obj):
        return obj.items.count()

    @extend_schema_field(serializers.CharField)
    def get_time_remaining(self, obj):
        if obj.status == 'PENDING' and obj.created_at:
            elapsed = timezone.now() - obj.created_at
            remaining = max(0, 15 - elapsed.seconds // 60)
            return f"{remaining} minutes"
        return None

    @extend_schema_field(serializers.CharField)
    def get_first_item_title(self, obj):
        """Titre du premier article."""
        first = obj.items.first()
        return first.offer.title if first else None

    @extend_schema_field(serializers.CharField)
    def get_first_item_image(self, obj):
        """Image du premier article — URL absolue."""
        first = obj.items.first()
        if first and first.offer.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(first.offer.image.url)
            return first.offer.image.url
        return None


class OrderDetailSerializer(serializers.ModelSerializer):
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
        if obj.status == 'PENDING' and obj.created_at:
            elapsed = timezone.now() - obj.created_at
            remaining_seconds = max(0, 15 * 60 - elapsed.seconds)
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            return f"{minutes:02d}:{seconds:02d}"
        return None

    @extend_schema_field(serializers.BooleanField)
    def get_can_cancel(self, obj):
        # Seulement PENDING — dès que confirmé plus d'annulation
        return obj.status == 'PENDING'

    @extend_schema_field(serializers.BooleanField)
    def get_can_confirm(self, obj):
        return obj.status == 'PENDING'


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)
    order_number = serializers.CharField(read_only=True)
    pickup_code = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = ['order_number', 'pickup_code', 'status', 'created_at', 'notes', 'items']

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Au moins un article est requis.")
        return value

    def validate(self, data):
        items = data.get('items', [])
        if not items:
            return data

        first_offer = items[0]['offer']
        partner = first_offer.partner
        total_amount = 0
        items_details = []

        for item in items:
            offer = item['offer']
            quantity = item['quantity']

            if not offer.is_available:
                raise serializers.ValidationError(
                    f"L'offre '{offer.title}' n'est plus disponible."
                )
            if quantity > offer.remaining_quantity:
                raise serializers.ValidationError(
                    f"L'offre '{offer.title}' n'a que {offer.remaining_quantity} disponible(s)."
                )
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
        items_details = validated_data.pop('items_details')
        validated_data.pop('items')
        validated_data['client'] = self.context['request'].user
        validated_data['partner'] = validated_data.pop('partner')
        validated_data['total_amount'] = validated_data.pop('total_amount')
        validated_data['status'] = Order.Status.PENDING

        order = Order.objects.create(**validated_data)

        for item_data in items_details:
            offer = item_data['offer']
            quantity = item_data['quantity']
            offer.reserve(quantity)
            OrderItem.objects.create(
                order=order,
                offer=offer,
                quantity=quantity,
                unit_price=offer.discounted_price
            )

        return order


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status', 'cancellation_reason']
        extra_kwargs = {'cancellation_reason': {'required': False}}

    def validate(self, data):
        order = self.instance
        new_status = data.get('status')
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
        if new_status == 'CANCELLED' and not data.get('cancellation_reason'):
            raise serializers.ValidationError(
                "Une raison d'annulation est requise."
            )
        return data

    def update(self, instance, validated_data):
        new_status = validated_data.get('status')
        if new_status == 'CONFIRMED':
            instance.confirmed_at = timezone.now()
        elif new_status == 'PICKED_UP':
            instance.picked_up_at = timezone.now()
        elif new_status == 'CANCELLED':
            instance.cancelled_at = timezone.now()
            for item in instance.items.all():
                item.offer.release_reservation(item.quantity)
        return super().update(instance, validated_data)


class OrderStatsSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    pending_orders = serializers.IntegerField()
    confirmed_orders = serializers.IntegerField()
    ready_orders = serializers.IntegerField()
    picked_up_orders = serializers.IntegerField()
    cancelled_orders = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=12, decimal_places=2)
    average_order_value = serializers.DecimalField(max_digits=8, decimal_places=2)
    most_ordered_items = serializers.ListField(child=serializers.DictField())


class OrderPickupRequest(serializers.Serializer):
    pickup_code = serializers.CharField(
        required=False, allow_blank=True,
        max_length=6, min_length=6,
        help_text="Code de retrait à 6 chiffres (optionnel)"
    )
    notes = serializers.CharField(
        required=False, allow_blank=True,
        max_length=255,
        help_text="Notes supplémentaires sur le retrait"
    )

    class Meta:
        ref_name = "OrderPickupRequest"

    def validate_pickup_code(self, value):
        if value and not value.isdigit():
            raise serializers.ValidationError(
                "Le code de retrait doit contenir uniquement des chiffres"
            )
        if value and len(value) != 6:
            raise serializers.ValidationError(
                "Le code de retrait doit contenir exactement 6 chiffres"
            )
        return value