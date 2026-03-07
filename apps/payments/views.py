from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Payment
from .serializers import (
    PaymentListSerializer, PaymentDetailSerializer, PaymentCreateSerializer,
    PaymentProcessSerializer, PaymentStatusUpdateSerializer,
    PaymentRefundSerializer, PaymentStatsSerializer, BalanceCheckResponseSerializer
)
from .permissions import IsPaymentOwnerOrReadOnly, CanCreatePayment, CanProcessPayment
from .services import MobileMoneySimulator


@extend_schema(
    tags=['payments'],
    summary="Liste des paiements",
    description="Retourne la liste des paiements de l'utilisateur connecté.",
    parameters=[
        OpenApiParameter(name='status', description='Filtrer par statut', required=False, type=str),
        OpenApiParameter(name='payment_method', description='Filtrer par méthode', required=False, type=str),
        OpenApiParameter(name='from_date', description='Date de début', required=False, type=str),
        OpenApiParameter(name='to_date', description='Date de fin', required=False, type=str),
    ],
)
class PaymentListView(generics.ListAPIView):
    """
    Liste des paiements de l'utilisateur connecté.
    - Client : voit ses paiements
    - Restaurateur : voit les paiements de ses restaurants
    - Admin : voit tous les paiements
    """
    serializer_class = PaymentListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_method']
    ordering_fields = ['created_at', 'amount']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        if user.role == 'ADMIN':
            queryset = Payment.objects.all()
        elif user.role == 'RESTAURANT':
            queryset = Payment.objects.filter(order__restaurant__owner=user)
        else:
            queryset = Payment.objects.filter(order__client=user)
        
        # Filtres supplémentaires
        from_date = self.request.query_params.get('from_date')
        to_date = self.request.query_params.get('to_date')
        
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        
        return queryset.select_related('order', 'order__client', 'order__restaurant')


@extend_schema(
    tags=['payments'],
    summary="Créer un paiement",
    description="Crée un nouveau paiement pour une commande.",
)
class PaymentCreateView(generics.CreateAPIView):
    """
    Crée un nouveau paiement.
    """
    serializer_class = PaymentCreateSerializer
    permission_classes = [permissions.IsAuthenticated, CanCreatePayment]


@extend_schema(
    tags=['payments'],
    summary="Détails d'un paiement",
    description="Retourne les détails d'un paiement spécifique.",
)
class PaymentDetailView(generics.RetrieveAPIView):
    """
    Détails d'un paiement.
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentDetailSerializer
    permission_classes = [permissions.IsAuthenticated, IsPaymentOwnerOrReadOnly]


@extend_schema(
    tags=['payments'],
    summary="Traiter un paiement",
    description="Traite un paiement (simulation Mobile Money).",
    request=PaymentProcessSerializer,
    responses={
        200: OpenApiExample(
            'Succès',
            value={
                'success': True,
                'message': 'Paiement effectué avec succès',
                'transaction_id': 'TXN_20250225123045_ABC123',
                'payment': {...}
            }
        ),
        400: OpenApiExample(
            'Échec',
            value={
                'success': False,
                'message': 'Solde insuffisant',
                'payment': {...}
            }
        )
    }
)
class PaymentProcessView(APIView):
    """
    Traite un paiement (simulation Mobile Money).
    """
    permission_classes = [permissions.IsAuthenticated, CanProcessPayment]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        serializer = PaymentProcessSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        action = serializer.validated_data['action']
        
        # Vérifier que le paiement est en attente
        if payment.status != 'PENDING':
            return Response(
                {'error': f'Ce paiement a déjà le statut {payment.status}.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Simulation selon la méthode
        if payment.payment_method in ['TMONEY', 'FLOOZ']:
            result = MobileMoneySimulator.process_payment(
                payment.phone_number,
                float(payment.amount),
                payment.payment_method
            )
        else:
            # Paiement en espèces - succès immédiat
            result = {
                'success': True,
                'message': 'Paiement en espèces enregistré',
                'transaction_id': f"CASH_{payment.transaction_id}"
            }
        
        # Mise à jour du statut
        if result['success']:
            payment.status = 'SUCCESS'
            payment.paid_at = timezone.now()
            payment.details['provider_response'] = result
            
            # Confirmer la commande associée
            payment.order.status = 'CONFIRMED'
            payment.order.confirmed_at = timezone.now()
            payment.order.save()
        else:
            payment.status = 'FAILED'
            payment.failed_reason = result['message']
            payment.details['provider_response'] = result
        
        payment.save()
        
        response_data = {
            'success': result['success'],
            'message': result['message'],
            'payment': PaymentDetailSerializer(payment).data
        }
        
        if result['success']:
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response(response_data, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    tags=['payments'],
    summary="Vérifier le solde",
    description="Simule la vérification de solde Mobile Money.",
    parameters=[
        OpenApiParameter(name='phone', description='Numéro de téléphone', required=True, type=str),
    ],
    responses={
        200: BalanceCheckResponseSerializer,  
        400: OpenApiResponse(description="Paramètre manquant"),
    }
)
class PaymentBalanceCheckView(APIView):
    """
    Vérifie le solde Mobile Money (simulation).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        phone = request.query_params.get('phone')
        
        if not phone:
            return Response(
                {'error': 'Le paramètre phone est requis.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        result = MobileMoneySimulator.check_balance(phone)
        return Response(result)


@extend_schema(
    tags=['payments'],
    summary="Rembourser un paiement",
    description="Rembourse un paiement (admin uniquement).",
    request=PaymentRefundSerializer,
)
class PaymentRefundView(APIView):
    """
    Rembourse un paiement (admin uniquement).
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        payment = get_object_or_404(Payment, pk=pk)
        serializer = PaymentRefundSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier que le paiement peut être remboursé
        if payment.status != 'SUCCESS':
            return Response(
                {'error': 'Seuls les paiements réussis peuvent être remboursés.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Simulation du remboursement
        if payment.payment_method in ['TMONEY', 'FLOZ']:
            result = MobileMoneySimulator.refund_payment(
                payment.transaction_id,
                float(payment.amount)
            )
        else:
            # Remboursement en espèces
            result = {
                'success': True,
                'message': 'Remboursement en espèces enregistré'
            }
        
        if result['success']:
            payment.status = 'FAILED'  # Ou un statut REFUNDED si vous l'ajoutez
            payment.details['refund'] = {
                'reason': serializer.validated_data['reason'],
                'timestamp': timezone.now().isoformat(),
                'result': result
            }
            payment.save()
            
            # Notifier le client (optionnel)
            if serializer.validated_data.get('notify_client'):
                # Logique de notification à implémenter
                pass
            
            return Response({
                'success': True,
                'message': 'Remboursement effectué avec succès',
                'payment': PaymentDetailSerializer(payment).data
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['payments'],
    summary="Mettre à jour le statut",
    description="Met à jour le statut d'un paiement (admin uniquement).",
    request=PaymentStatusUpdateSerializer,
    responses={200: PaymentDetailSerializer}
)
class PaymentStatusUpdateView(generics.UpdateAPIView):
    """
    Met à jour le statut d'un paiement (admin uniquement).
    """
    queryset = Payment.objects.all()
    serializer_class = PaymentStatusUpdateSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema(
    tags=['payments'],
    summary="Statistiques des paiements",
    description="Retourne des statistiques sur les paiements.",
)
class PaymentStatsView(APIView):
    """
    Statistiques des paiements.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Filtrer les paiements selon l'utilisateur
        if user.role == 'ADMIN':
            payments = Payment.objects.all()
        elif user.role == 'RESTAURANT':
            payments = Payment.objects.filter(order__restaurant__owner=user)
        else:
            payments = Payment.objects.filter(order__client=user)
        
        # Période (optionnelle)
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timezone.timedelta(days=days)
        recent_payments = payments.filter(created_at__gte=since)
        
        # Statistiques globales
        total_payments = payments.count()
        total_amount = payments.aggregate(total=Sum('amount'))['total'] or 0
        
        successful = payments.filter(status='SUCCESS')
        successful_count = successful.count()
        successful_amount = successful.aggregate(total=Sum('amount'))['total'] or 0
        
        # Statistiques par méthode
        method_breakdown = {}
        for method in ['TMONEY', 'FLOZ', 'CASH']:
            method_payments = payments.filter(payment_method=method)
            method_breakdown[method] = {
                'count': method_payments.count(),
                'amount': float(method_payments.aggregate(total=Sum('amount'))['total'] or 0),
                'success_rate': (method_payments.filter(status='SUCCESS').count() / 
                               method_payments.count() * 100 if method_payments.count() > 0 else 0)
            }
        
        # Statistiques quotidiennes
        daily_stats = []
        for i in range(days):
            day = since.date() + timezone.timedelta(days=i)
            day_payments = payments.filter(created_at__date=day)
            daily_stats.append({
                'date': day.isoformat(),
                'count': day_payments.count(),
                'amount': float(day_payments.aggregate(total=Sum('amount'))['total'] or 0),
                'successful': day_payments.filter(status='SUCCESS').count()
            })
        
        stats = {
            'total_payments': total_payments,
            'total_amount': float(total_amount),
            'successful_payments': successful_count,
            'successful_amount': float(successful_amount),
            'failed_payments': payments.filter(status='FAILED').count(),
            'pending_payments': payments.filter(status='PENDING').count(),
            'payment_method_breakdown': method_breakdown,
            'daily_stats': daily_stats
        }
        
        serializer = PaymentStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)


@extend_schema(
    tags=['payments'],
    summary="Paiement d'une commande",
    description="Crée et traite directement un paiement pour une commande.",
)
class OrderPaymentView(APIView):
    """
    Crée et traite directement un paiement pour une commande.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        from apps.orders.models import Order
        
        order = get_object_or_404(Order, id=order_id)
        
        # Vérifier que l'utilisateur est le client
        if order.client != request.user:
            return Response(
                {'error': 'Vous ne pouvez payer que vos propres commandes.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Vérifier que la commande peut être payée
        if order.status != 'PENDING':
            return Response(
                {'error': f'Cette commande ne peut pas être payée (statut: {order.status}).'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier qu'il n'y a pas déjà un paiement
        if hasattr(order, 'payment'):
            return Response({
                'error': 'Un paiement existe déjà pour cette commande.',
                'payment_id': order.payment.id
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Créer le paiement
        payment_data = {
            'order': order.id,
            'amount': order.total_amount,
            'payment_method': request.data.get('payment_method', 'CASH'),
            'phone_number': request.data.get('phone_number')
        }
        
        create_serializer = PaymentCreateSerializer(
            data=payment_data,
            context={'request': request}
        )
        
        if not create_serializer.is_valid():
            return Response(create_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        payment = create_serializer.save()
        
        # Traiter le paiement automatiquement
        if payment.payment_method == 'CASH':
            # Paiement en espèces - succès immédiat
            payment.status = 'SUCCESS'
            payment.paid_at = timezone.now()
            payment.save()
            
            order.status = 'CONFIRMED'
            order.confirmed_at = timezone.now()
            order.save()
            
            return Response({
                'success': True,
                'message': 'Commande confirmée. Paiement à effectuer au retrait.',
                'payment': PaymentDetailSerializer(payment).data
            })
        else:
            # Mobile Money - simulation
            result = MobileMoneySimulator.process_payment(
                payment.phone_number,
                float(payment.amount),
                payment.payment_method
            )
            
            if result['success']:
                payment.status = 'SUCCESS'
                payment.paid_at = timezone.now()
                payment.details['provider_response'] = result
                payment.save()
                
                order.status = 'CONFIRMED'
                order.confirmed_at = timezone.now()
                order.save()
                
                return Response({
                    'success': True,
                    'message': 'Paiement effectué avec succès',
                    'payment': PaymentDetailSerializer(payment).data
                })
            else:
                payment.status = 'FAILED'
                payment.failed_reason = result['message']
                payment.details['provider_response'] = result
                payment.save()
                
                return Response({
                    'success': False,
                    'message': result['message'],
                    'payment': PaymentDetailSerializer(payment).data
                }, status=status.HTTP_400_BAD_REQUEST)