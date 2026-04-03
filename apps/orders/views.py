from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter,OpenApiResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Order, OrderItem
from .serializers import (
    OrderListSerializer, OrderDetailSerializer, OrderCreateSerializer,
    OrderStatusUpdateSerializer, OrderStatsSerializer, OrderPickupRequest
)
from .permissions import IsOrderClientOrReadOnly, IsOrderPartnerOrClient, CanCreateOrder

from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count


from apps.orders.models import Order
from apps.orders.serializers import OrderListSerializer, OrderDetailSerializer
from apps.partners.models import Partner
from apps.accounts.permissions import IsPartnerOrAdmin


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



@extend_schema(
    tags=['partner-orders'],
    summary="Liste des commandes du partenaire",
    description="Retourne toutes les commandes des établissements de l'utilisateur connecté (rôle PARTNER).",
    parameters=[
        OpenApiParameter(name='partner_id', description='ID du partenaire spécifique (optionnel)', required=False, type=int),
        OpenApiParameter(name='status', description='Filtrer par statut', required=False, type=str),
        OpenApiParameter(name='from_date', description='Date de début (YYYY-MM-DD)', required=False, type=str),
        OpenApiParameter(name='to_date', description='Date de fin (YYYY-MM-DD)', required=False, type=str),
        OpenApiParameter(name='search', description='Recherche par numéro de commande ou nom client', required=False, type=str),
        OpenApiParameter(name='ordering', description='Tri (ex: -created_at, total_amount)', required=False, type=str),
        OpenApiParameter(name='page', description='Numéro de page', required=False, type=int),
        OpenApiParameter(name='page_size', description='Nombre d\'éléments par page', required=False, type=int),
    ],
    responses={
        200: OpenApiResponse(
            description="Liste paginée des commandes",
            response=OrderListSerializer(many=True)
        ),
        403: OpenApiResponse(description="Non autorisé"),
    }
)
class PartnerOrdersListView(generics.ListAPIView):
    """
    Vue pour les partenaires : récupère les commandes de leurs établissements.
    Un partenaire peut avoir plusieurs établissements.
    """
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated, IsPartnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order_number', 'client__first_name', 'client__last_name', 'client__phone_number']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        # Vérifier que l'utilisateur est bien un partenaire
        if user.role != 'PARTNER' and not user.is_staff:
            return Order.objects.none()
        
        # Récupérer tous les partenaires de l'utilisateur
        partners = Partner.objects.filter(owner=user)
        partner_ids = partners.values_list('id', flat=True)
        
        # Base queryset : commandes de tous les partenaires de l'utilisateur
        queryset = Order.objects.filter(
            partner_id__in=partner_ids
        ).select_related(
            'client', 'partner'
        ).prefetch_related('items', 'items__offer')
        
        # Filtre optionnel par partenaire spécifique
        partner_id = self.request.query_params.get('partner_id')
        if partner_id:
            # Vérifier que le partenaire appartient bien à l'utilisateur
            if int(partner_id) in partner_ids:
                queryset = queryset.filter(partner_id=partner_id)
            else:
                # Si l'ID ne correspond pas à un partenaire de l'utilisateur
                return Order.objects.none()
        
        # Filtre par statut
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filtre par date
        from_date = self.request.query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        
        to_date = self.request.query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        
        return queryset

    def list(self, request, *args, **kwargs):
        """Override pour ajouter des métadonnées supplémentaires."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Statistiques rapides pour l'en-tête
        total_orders = queryset.count()
        total_revenue = queryset.filter(
            status='PICKED_UP'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Compter par statut
        pending_count = queryset.filter(status='PENDING').count()
        confirmed_count = queryset.filter(status='CONFIRMED').count()
        ready_count = queryset.filter(status='READY').count()
        completed_count = queryset.filter(status='PICKED_UP').count()
        cancelled_count = queryset.filter(status='CANCELLED').count()
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(queryset, many=True)
            response_data = {
                'count': total_orders,
                'results': serializer.data
            }
        
        # Ajouter les métadonnées
        response_data['metadata'] = {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'counts_by_status': {
                'PENDING': pending_count,
                'CONFIRMED': confirmed_count,
                'READY': ready_count,
                'PICKED_UP': completed_count,
                'CANCELLED': cancelled_count,
            }
        }
        
        # Informations sur les partenaires disponibles
        partners = Partner.objects.filter(owner=request.user).values('id', 'name')
        response_data['available_partners'] = list(partners)
        
        return Response(response_data)


@extend_schema(
    tags=['partner-orders'],
    summary="Détails d'une commande",
    description="Retourne les détails complets d'une commande spécifique d'un partenaire.",
)
class PartnerOrderDetailView(generics.RetrieveAPIView):
    """
    Détails d'une commande pour un partenaire.
    Vérifie que la commande appartient bien à un établissement de l'utilisateur.
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsPartnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        partners = Partner.objects.filter(owner=user)
        partner_ids = partners.values_list('id', flat=True)
        
        return Order.objects.filter(
            partner_id__in=partner_ids
        ).select_related(
            'client', 'partner'
        ).prefetch_related('items', 'items__offer')


@extend_schema(
    tags=['partner-orders'],
    summary="Statistiques des commandes",
    description="Retourne des statistiques détaillées sur les commandes du partenaire.",
    parameters=[
        OpenApiParameter(name='partner_id', description='ID du partenaire (optionnel)', required=False, type=int),
        OpenApiParameter(name='days', description='Nombre de jours (défaut: 30)', required=False, type=int),
    ],
)
class PartnerOrdersStatsView(APIView):
    """
    Statistiques détaillées des commandes pour un partenaire.
    """
    permission_classes = [permissions.IsAuthenticated, IsPartnerOrAdmin]

    def get(self, request):
        user = request.user
        partners = Partner.objects.filter(owner=user)
        partner_ids = partners.values_list('id', flat=True)
        
        # Filtrer par partenaire spécifique si demandé
        partner_id = request.query_params.get('partner_id')
        if partner_id and int(partner_id) in partner_ids:
            partner_ids = [int(partner_id)]
        
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timezone.timedelta(days=days)
        
        # Commandes de la période
        orders = Order.objects.filter(
            partner_id__in=partner_ids,
            created_at__gte=since
        )
        
        # Statistiques globales
        total_orders = orders.count()
        total_revenue = orders.filter(
            status='PICKED_UP'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Commandes par statut
        orders_by_status = {}
        for status_code, _ in Order.Status.choices:
            count = orders.filter(status=status_code).count()
            if count > 0:
                orders_by_status[status_code] = count
        
        # Commandes par jour
        daily_orders = orders.extra(
            {'day': "date(created_at)"}
        ).values('day').annotate(
            count=Count('id'),
            revenue=Sum('total_amount', filter=Q(status='PICKED_UP'))
        ).order_by('day')
        
        # Top clients
        top_clients = orders.filter(
            status='PICKED_UP'
        ).values(
            'client__id', 'client__first_name', 'client__last_name'
        ).annotate(
            order_count=Count('id'),
            total_spent=Sum('total_amount')
        ).order_by('-total_spent')[:5]
        
        # Top offres vendues
        from apps.orders.models import OrderItem
        top_offers = OrderItem.objects.filter(
            order__partner_id__in=partner_ids,
            order__status='PICKED_UP',
            order__created_at__gte=since
        ).values(
            'offer__id', 'offer__title'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('subtotal')
        ).order_by('-total_quantity')[:5]
        
        return Response({
            'period': {
                'days': days,
                'start': since.date().isoformat(),
                'end': timezone.now().date().isoformat(),
            },
            'overview': {
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'average_order_value': float(total_revenue / total_orders) if total_orders > 0 else 0,
            },
            'orders_by_status': orders_by_status,
            'daily_orders': [
                {
                    'date': item['day'],
                    'count': item['count'],
                    'revenue': float(item['revenue']) if item['revenue'] else 0,
                }
                for item in daily_orders
            ],
            'top_clients': [
                {
                    'client_id': item['client__id'],
                    'name': f"{item['client__first_name']} {item['client__last_name']}".strip(),
                    'order_count': item['order_count'],
                    'total_spent': float(item['total_spent']),
                }
                for item in top_clients
            ],
            'top_offers': [
                {
                    'offer_id': item['offer__id'],
                    'title': item['offer__title'],
                    'total_quantity': item['total_quantity'],
                    'total_revenue': float(item['total_revenue']),
                }
                for item in top_offers
            ],
        })


@extend_schema(
    tags=['partner-orders'],
    summary="Mettre à jour le statut d'une commande",
    description="Permet au partenaire de mettre à jour le statut d'une commande.",
)
class PartnerOrderStatusUpdateView(APIView):
    """
    Mise à jour du statut d'une commande par le partenaire.
    """
    permission_classes = [permissions.IsAuthenticated, IsPartnerOrAdmin]

    def patch(self, request, pk):
        # Vérifier que la commande appartient au partenaire
        user = request.user
        partners = Partner.objects.filter(owner=user)
        partner_ids = partners.values_list('id', flat=True)
        
        order = get_object_or_404(
            Order,
            id=pk,
            partner_id__in=partner_ids
        )
        
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {'error': 'Le statut est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier les transitions valides
        valid_transitions = {
            'PENDING': ['CONFIRMED', 'CANCELLED'],
            'CONFIRMED': ['READY', 'CANCELLED'],
            'READY': ['PICKED_UP', 'CANCELLED'],
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            return Response(
                {'error': f'Transition de {order.status} vers {new_status} non autorisée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mettre à jour le statut
        order.status = new_status
        
        # Mettre à jour les timestamps
        if new_status == 'CONFIRMED':
            order.confirmed_at = timezone.now()
        elif new_status == 'READY':
            order.ready_at = timezone.now()
        elif new_status == 'PICKED_UP':
            order.picked_up_at = timezone.now()
        elif new_status == 'CANCELLED':
            order.cancelled_at = timezone.now()
            order.cancellation_reason = request.data.get('reason', 'Annulée par le partenaire')
        
        order.save()
        
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)








@extend_schema(
    tags=['partner-orders'],
    summary="Commandes d'un établissement",
    description="Retourne toutes les commandes d'un établissement spécifique (le propriétaire doit être connecté).",
    parameters=[
        OpenApiParameter(name='status', description='Filtrer par statut', required=False, type=str),
        OpenApiParameter(name='from_date', description='Date de début (YYYY-MM-DD)', required=False, type=str),
        OpenApiParameter(name='to_date', description='Date de fin (YYYY-MM-DD)', required=False, type=str),
        OpenApiParameter(name='search', description='Recherche par numéro de commande ou nom client', required=False, type=str),
        OpenApiParameter(name='ordering', description='Tri (ex: -created_at, total_amount)', required=False, type=str),
        OpenApiParameter(name='page', description='Numéro de page', required=False, type=int),
        OpenApiParameter(name='page_size', description='Nombre d\'éléments par page', required=False, type=int),
    ],
    responses={
        200: OpenApiResponse(
            description="Liste paginée des commandes",
            response=OrderListSerializer(many=True)
        ),
        403: OpenApiResponse(description="Non autorisé - Vous n'êtes pas le propriétaire de cet établissement"),
        404: OpenApiResponse(description="Établissement non trouvé"),
    }
)
class PartnerEstablishmentOrdersView(generics.ListAPIView):
    """
    Vue pour récupérer les commandes d'un établissement spécifique.
    Vérifie que l'utilisateur connecté est bien le propriétaire du partenaire.
    """
    serializer_class = OrderListSerializer
    permission_classes = [permissions.IsAuthenticated, IsPartnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['order_number', 'client__first_name', 'client__last_name', 'client__phone_number']
    ordering_fields = ['created_at', 'total_amount', 'status']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        # Récupérer l'ID du partenaire depuis l'URL
        partner_id = self.kwargs.get('partner_id')
        
        # Vérifier que le partenaire existe et appartient à l'utilisateur
        partner = get_object_or_404(Partner, id=partner_id)
        
        # Vérifier que l'utilisateur est bien le propriétaire
        if partner.owner != user and not user.is_staff:
            return Order.objects.none()
        
        # Base queryset : commandes de ce partenaire uniquement
        queryset = Order.objects.filter(
            partner=partner
        ).select_related(
            'client', 'partner'
        ).prefetch_related('items', 'items__offer')
        
        # Filtre par statut
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filtre par date
        from_date = self.request.query_params.get('from_date')
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        
        to_date = self.request.query_params.get('to_date')
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        
        return queryset

    def list(self, request, *args, **kwargs):
        """Override pour ajouter des métadonnées sur l'établissement."""
        partner_id = self.kwargs.get('partner_id')
        partner = get_object_or_404(Partner, id=partner_id)
        
        queryset = self.filter_queryset(self.get_queryset())
        
        # Statistiques rapides pour cet établissement
        total_orders = queryset.count()
        total_revenue = queryset.filter(
            status='PICKED_UP'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Compter par statut
        pending_count = queryset.filter(status='PENDING').count()
        confirmed_count = queryset.filter(status='CONFIRMED').count()
        ready_count = queryset.filter(status='READY').count()
        completed_count = queryset.filter(status='PICKED_UP').count()
        cancelled_count = queryset.filter(status='CANCELLED').count()
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(queryset, many=True)
            response_data = {
                'count': total_orders,
                'results': serializer.data
            }
        
        # Ajouter les informations de l'établissement et les métadonnées
        response_data['establishment'] = {
            'id': partner.id,
            'name': partner.name,
            'quarter': partner.quarter,
            'address': partner.address,
            'phone': partner.phone,
            'is_open': partner.is_open_now(),
            'status': partner.status,
        }
        
        response_data['metadata'] = {
            'total_orders': total_orders,
            'total_revenue': float(total_revenue),
            'average_order_value': float(total_revenue / total_orders) if total_orders > 0 else 0,
            'counts_by_status': {
                'PENDING': pending_count,
                'CONFIRMED': confirmed_count,
                'READY': ready_count,
                'PICKED_UP': completed_count,
                'CANCELLED': cancelled_count,
            }
        }
        
        return Response(response_data)


@extend_schema(
    tags=['partner-orders'],
    summary="Détails d'une commande pour un établissement",
    description="Retourne les détails d'une commande spécifique, en vérifiant qu'elle appartient bien à l'établissement.",
)
class PartnerEstablishmentOrderDetailView(generics.RetrieveAPIView):
    """
    Détails d'une commande pour un établissement spécifique.
    """
    serializer_class = OrderDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsPartnerOrAdmin]

    def get_queryset(self):
        user = self.request.user
        partner_id = self.kwargs.get('partner_id')
        
        # Vérifier que le partenaire existe et appartient à l'utilisateur
        partner = get_object_or_404(Partner, id=partner_id)
        
        if partner.owner != user and not user.is_staff:
            return Order.objects.none()
        
        return Order.objects.filter(
            partner=partner
        ).select_related(
            'client', 'partner'
        ).prefetch_related('items', 'items__offer')


@extend_schema(
    tags=['partner-orders'],
    summary="Statistiques d'un établissement",
    description="Retourne des statistiques détaillées sur les commandes d'un établissement.",
    parameters=[
        OpenApiParameter(name='days', description='Nombre de jours (défaut: 30)', required=False, type=int),
    ],
)
class PartnerEstablishmentOrdersStatsView(APIView):
    """
    Statistiques détaillées des commandes pour un établissement.
    """
    permission_classes = [permissions.IsAuthenticated, IsPartnerOrAdmin]

    def get(self, request, partner_id):
        user = request.user
        
        # Vérifier que le partenaire existe et appartient à l'utilisateur
        partner = get_object_or_404(Partner, id=partner_id)
        
        if partner.owner != user and not user.is_staff:
            return Response(
                {"detail": "Vous n'êtes pas autorisé à consulter les statistiques de cet établissement."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timezone.timedelta(days=days)
        
        # Commandes de la période
        orders = Order.objects.filter(
            partner=partner,
            created_at__gte=since
        )
        
        # Statistiques globales
        total_orders = orders.count()
        total_revenue = orders.filter(
            status='PICKED_UP'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Commandes par statut
        orders_by_status = {}
        for status_code, _ in Order.Status.choices:
            count = orders.filter(status=status_code).count()
            if count > 0:
                orders_by_status[status_code] = count
        
        # Commandes par jour
        daily_orders = orders.extra(
            {'day': "date(created_at)"}
        ).values('day').annotate(
            count=Count('id'),
            revenue=Sum('total_amount', filter=Q(status='PICKED_UP'))
        ).order_by('day')
        
        # Top clients
        top_clients = orders.filter(
            status='PICKED_UP'
        ).values(
            'client__id', 'client__first_name', 'client__last_name'
        ).annotate(
            order_count=Count('id'),
            total_spent=Sum('total_amount')
        ).order_by('-total_spent')[:5]
        
        # Top offres vendues
        from apps.orders.models import OrderItem
        top_offers = OrderItem.objects.filter(
            order__partner=partner,
            order__status='PICKED_UP',
            order__created_at__gte=since
        ).values(
            'offer__id', 'offer__title'
        ).annotate(
            total_quantity=Sum('quantity'),
            total_revenue=Sum('subtotal')
        ).order_by('-total_quantity')[:5]
        
        # Informations sur l'établissement
        establishment_info = {
            'id': partner.id,
            'name': partner.name,
            'quarter': partner.quarter,
            'address': partner.address,
            'phone': partner.phone,
            'opening_time': partner.opening_time.strftime('%H:%M') if partner.opening_time else None,
            'closing_time': partner.closing_time.strftime('%H:%M') if partner.closing_time else None,
            'is_open': partner.is_open_now(),
            'status': partner.status,
        }
        
        return Response({
            'establishment': establishment_info,
            'period': {
                'days': days,
                'start': since.date().isoformat(),
                'end': timezone.now().date().isoformat(),
            },
            'overview': {
                'total_orders': total_orders,
                'total_revenue': float(total_revenue),
                'average_order_value': float(total_revenue / total_orders) if total_orders > 0 else 0,
            },
            'orders_by_status': orders_by_status,
            'daily_orders': [
                {
                    'date': item['day'],
                    'count': item['count'],
                    'revenue': float(item['revenue']) if item['revenue'] else 0,
                }
                for item in daily_orders
            ],
            'top_clients': [
                {
                    'client_id': item['client__id'],
                    'name': f"{item['client__first_name']} {item['client__last_name']}".strip(),
                    'order_count': item['order_count'],
                    'total_spent': float(item['total_spent']),
                }
                for item in top_clients
            ],
            'top_offers': [
                {
                    'offer_id': item['offer__id'],
                    'title': item['offer__title'],
                    'total_quantity': item['total_quantity'],
                    'total_revenue': float(item['total_revenue']),
                }
                for item in top_offers
            ],
        })


@extend_schema(
    tags=['partner-orders'],
    summary="Mettre à jour le statut d'une commande",
    description="Permet au propriétaire de l'établissement de mettre à jour le statut d'une commande.",
)
class PartnerEstablishmentOrderStatusUpdateView(APIView):
    """
    Mise à jour du statut d'une commande par le propriétaire de l'établissement.
    """
    permission_classes = [permissions.IsAuthenticated, IsPartnerOrAdmin]

    def patch(self, request, partner_id, order_id):
        user = request.user
        
        # Vérifier que le partenaire existe et appartient à l'utilisateur
        partner = get_object_or_404(Partner, id=partner_id)
        
        if partner.owner != user and not user.is_staff:
            return Response(
                {"detail": "Vous n'êtes pas autorisé à modifier les commandes de cet établissement."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Récupérer la commande
        order = get_object_or_404(Order, id=order_id, partner=partner)
        
        new_status = request.data.get('status')
        if not new_status:
            return Response(
                {'error': 'Le statut est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier les transitions valides
        valid_transitions = {
            'PENDING': ['CONFIRMED', 'CANCELLED'],
            'CONFIRMED': ['READY', 'CANCELLED'],
            'READY': ['PICKED_UP', 'CANCELLED'],
        }
        
        if new_status not in valid_transitions.get(order.status, []):
            return Response(
                {'error': f'Transition de {order.status} vers {new_status} non autorisée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Mettre à jour le statut
        order.status = new_status
        
        # Mettre à jour les timestamps
        if new_status == 'CONFIRMED':
            order.confirmed_at = timezone.now()
        elif new_status == 'READY':
            order.ready_at = timezone.now()
        elif new_status == 'PICKED_UP':
            order.picked_up_at = timezone.now()
        elif new_status == 'CANCELLED':
            order.cancelled_at = timezone.now()
            order.cancellation_reason = request.data.get('reason', 'Annulée par le partenaire')
        
        order.save()
        
        serializer = OrderDetailSerializer(order)
        return Response(serializer.data)