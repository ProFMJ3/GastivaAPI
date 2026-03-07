from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Order, OrderItem
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderStatusUpdateSerializer, OrderStatsSerializer, OrderPickupRequest
)
from .permissions import IsOrderClientOrReadOnly, IsOrderPartnerOrClient, CanCreateOrder


@extend_schema(
    tags=['orders'],
    summary="Liste des commandes",
    description="Retourne la liste des commandes de l'utilisateur connecté.",
    parameters=[
        OpenApiParameter(name='status', description='Filtrer par statut', required=False, type=str),
        OpenApiParameter(name='partner', description='Filtrer par partner', required=False, type=int),
        OpenApiParameter(name='from_date', description='Date de début (YYYY-MM-DD)', required=False, type=str),
        OpenApiParameter(name='to_date', description='Date de fin (YYYY-MM-DD)', required=False, type=str),
    ],
)


# class OrderListView(generics.ListAPIView):
#     """
#     Liste des commandes de l'utilisateur connecté.
#     - Client : voit ses commandes
#     - Restaurateur : voit les commandes de ses partners
#     - Admin : voit toutes les commandes
#     """
#     serializer_class = OrderListSerializer
#     filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
#     filterset_fields = ['status', 'partner']
#     ordering_fields = ['created_at', 'total_amount']
#     ordering = ['-created_at']

#     def get_queryset(self):
#         user = self.request.user
        
#         if user.role == 'ADMIN':
#             queryset = Order.objects.all()
#         elif user.role == 'PARTNER':
#             queryset = Order.objects.filter(partner__owner=user)
#         else:
#             queryset = Order.objects.filter(client=user)
        
#         # Filtres supplémentaires
#         from_date = self.request.query_params.get('from_date')
#         to_date = self.request.query_params.get('to_date')
        
#         if from_date:
#             queryset = queryset.filter(created_at__date__gte=from_date)
#         if to_date:
#             queryset = queryset.filter(created_at__date__lte=to_date)
        
#         return queryset.select_related('client', 'partner').prefetch_related('items')



class OrderListView(generics.ListAPIView):
    """
    Liste des commandes de l'utilisateur connecté.
    """
    serializer_class = OrderListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'partner']
    ordering_fields = ['created_at', 'total_amount']
    ordering = ['-created_at']

    def get_queryset(self):
        # Pour Swagger
        if getattr(self, 'swagger_fake_view', False):
            return Order.objects.none()
        
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
        
        if user.role == 'ADMIN':
            queryset = Order.objects.all()
        elif user.role == 'PARTNER':
            queryset = Order.objects.filter(partner__owner=user)
        else:
            queryset = Order.objects.filter(client=user)
        
        # Filtres supplémentaires
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        
        return queryset.select_related('client', 'partner').prefetch_related('items')
@extend_schema(
    tags=['orders'],
    summary="Créer une commande",
    description="Crée une nouvelle commande (réservé aux clients).",
    responses={
        201: OrderDetailSerializer,
        400: "Données invalides"
    }
)
class OrderCreateView(generics.CreateAPIView):
    """
    Crée une nouvelle commande.
    
    Retourne la commande créée avec :
    - order_number : Numéro de commande unique
    - pickup_code : Code à 6 chiffres pour le retrait
    - created_at : Date de création
    - status : Statut initial (PENDING)
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [permissions.IsAuthenticated, CanCreateOrder]

    def perform_create(self, serializer):
        """Surcharge pour logger la création."""
        order = serializer.save()
        
        print(f"Commande créée: {order.order_number} pour {order.client.get_full_name()}")

@extend_schema(
    tags=['orders'],
    summary="Détails d'une commande",
    description="Retourne les détails d'une commande spécifique.",
)
class OrderDetailView(generics.RetrieveAPIView):
    """
    Détails d'une commande.
    """
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsOrderClientOrReadOnly]


@extend_schema(
    tags=['orders'],
    summary="Mettre à jour le statut",
    description="Met à jour le statut d'une commande.",
    request=OrderStatusUpdateSerializer,
    responses={200: OrderDetailSerializer}
)
class OrderStatusUpdateView(APIView):
    """
    Met à jour le statut d'une commande.
    """
    permission_classes = [permissions.IsAuthenticated, IsOrderPartnerOrClient]

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderStatusUpdateSerializer(order, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(OrderDetailSerializer(order).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['orders'],
    summary="Annuler une commande",
    description="Annule une commande (client ou partner).",
    request=OrderStatusUpdateSerializer,
    responses={200: OrderDetailSerializer}
)
class OrderCancelView(APIView):
    """
    Annule une commande.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        # Vérifier les permissions
        if not (request.user == order.client or request.user == order.partner.owner or request.user.role == 'ADMIN'):
            return Response(
                {"detail": "Vous n'avez pas la permission d'annuler cette commande."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que la commande peut être annulée
        if order.status not in ['PENDING', 'CONFIRMED']:
            return Response(
                {"detail": f"Impossible d'annuler une commande avec le statut {order.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', 'Annulée par ' + ('le client' if request.user == order.client else 'le partner'))
        
        serializer = OrderStatusUpdateSerializer(
            order,
            data={'status': 'CANCELLED', 'cancellation_reason': reason},
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(OrderDetailSerializer(order).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['orders'],
    summary="Confirmer une commande",
    description="Confirme une commande (après paiement).",
)
class OrderConfirmView(APIView):
    """
    Confirme une commande.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        request=None,
        responses={200: OrderDetailSerializer}
    )

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        # Seul le partner peut confirmer
        if request.user != order.partner.owner and request.user.role != 'ADMIN':
            return Response(
                {"detail": "Seul le partner peut confirmer la commande."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status != 'PENDING':
            return Response(
                {"detail": f"Impossible de confirmer une commande avec le statut {order.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = OrderStatusUpdateSerializer(
            order,
            data={'status': 'CONFIRMED'},
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(OrderDetailSerializer(order).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['orders'],
    summary="Marquer comme prêt",
    description="Marque une commande comme prête pour le retrait.",
)
class OrderReadyView(APIView):
    """
    Marque une commande comme prête.
    """
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        request=None,
        responses={200: OrderDetailSerializer}
    )

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        if request.user != order.partner.owner and request.user.role != 'ADMIN':
            return Response(
                {"detail": "Seul le partner peut marquer la commande comme prête."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status != 'CONFIRMED':
            return Response(
                {"detail": f"Impossible de marquer comme prête une commande avec le statut {order.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = OrderStatusUpdateSerializer(
            order,
            data={'status': 'READY'},
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(OrderDetailSerializer(order).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['orders'],
    summary="Marquer comme retirée",
    description="Marque une commande comme retirée par le client.",
)
class OrderPickupView(APIView):
    """
    Marque une commande comme retirée.
    """
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        request= OrderPickupRequest,  
        responses={200: OrderDetailSerializer}
    )

    def post(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        
        # Le client ou le partner peut marquer comme retiré
        if not (request.user == order.client or request.user == order.partner.owner or request.user.role == 'ADMIN'):
            return Response(
                {"detail": "Vous n'avez pas la permission."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if order.status != 'READY':
            return Response(
                {"detail": f"Impossible de marquer comme retirée une commande avec le statut {order.status}."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier le code de retrait (optionnel)
        code = request.data.get('pickup_code')
        if code and code != order.pickup_code:
            return Response(
                {"detail": "Code de retrait invalide."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = OrderStatusUpdateSerializer(
            order,
            data={'status': 'PICKED_UP'},
            partial=True
        )
        
        if serializer.is_valid():
            serializer.save()
            return Response(OrderDetailSerializer(order).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['orders'],
    summary="Commandes en cours",
    description="Retourne les commandes en cours de l'utilisateur.",
)
class OrderActiveListView(generics.ListAPIView):
    """
    Commandes en cours (PENDING, CONFIRMED, READY).
    """
    serializer_class = OrderListSerializer

    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'partner':
            return Order.objects.filter(
                partner__owner=user,
                status__in=['PENDING', 'CONFIRMED', 'READY']
            ).select_related('client', 'partner')
        else:
            return Order.objects.filter(
                client=user,
                status__in=['PENDING', 'CONFIRMED', 'READY']
            ).select_related('client', 'partner')


@extend_schema(
    tags=['orders'],
    summary="Historique des commandes",
    description="Retourne l'historique des commandes terminées.",
)
class OrderHistoryListView(generics.ListAPIView):
    """
    Historique des commandes (PICKED_UP, CANCELLED).
    """
    serializer_class = OrderListSerializer

    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'partner':
            return Order.objects.filter(
                partner__owner=user,
                status__in=['PICKED_UP', 'CANCELLED']
            ).select_related('client', 'partner')
        else:
            return Order.objects.filter(
                client=user,
                status__in=['PICKED_UP', 'CANCELLED']
            ).select_related('client', 'partner')


@extend_schema(
    tags=['orders'],
    summary="Statistiques des commandes",
    description="Retourne des statistiques sur les commandes.",
)
class OrderStatsView(APIView):
    """
    Statistiques des commandes.
    """
    permission_classes = [permissions.IsAuthenticated]
    @extend_schema(
        responses={200: OrderStatsSerializer}  # À créer si nécessaire
    )

    def get(self, request):
        user = request.user
        
        if user.role == 'ADMIN':
            orders = Order.objects.all()
        elif user.role == 'partner':
            orders = Order.objects.filter(partner__owner=user)
        else:
            orders = Order.objects.filter(client=user)
        
        # Statistiques
        total_orders = orders.count()
        pending = orders.filter(status='PENDING').count()
        confirmed = orders.filter(status='CONFIRMED').count()
        ready = orders.filter(status='READY').count()
        picked_up = orders.filter(status='PICKED_UP').count()
        cancelled = orders.filter(status='CANCELLED').count()
        
        # Revenus
        completed_orders = orders.filter(status='PICKED_UP')
        total_revenue = completed_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Valeur moyenne
        avg_order = total_revenue / picked_up if picked_up > 0 else 0
        
        # Articles les plus commandés
        most_ordered = OrderItem.objects.filter(
            order__in=orders
        ).values(
            'offer__title'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_orders=Count('order', distinct=True)
        ).order_by('-total_quantity')[:5]
        
        stats = {
            'total_orders': total_orders,
            'pending_orders': pending,
            'confirmed_orders': confirmed,
            'ready_orders': ready,
            'picked_up_orders': picked_up,
            'cancelled_orders': cancelled,
            'total_revenue': total_revenue,
            'average_order_value': round(avg_order, 2),
            'most_ordered_items': [
                {
                    'title': item['offer__title'],
                    'total_quantity': item['total_quantity'],
                    'total_orders': item['total_orders']
                }
                for item in most_ordered
            ]
        }
        
        serializer = OrderStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)