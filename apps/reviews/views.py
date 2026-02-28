from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import Review
from .serializers import (
    ReviewListSerializer, ReviewDetailSerializer, ReviewCreateSerializer,
    ReviewUpdateSerializer, ReviewModerateSerializer, ReviewStatsSerializer,
    PartnerReviewStatsSerializer
)
from .permissions import IsReviewOwnerOrReadOnly, CanCreateReview, CanModerateReview
from apps.partners.models import Partner


@extend_schema(
    tags=['reviews'],
    summary="Liste des avis",
    description="Retourne la liste des avis publics.",
    parameters=[
        OpenApiParameter(name='partner', description='Filtrer par partenaire', required=False, type=int),
        OpenApiParameter(name='client', description='Filtrer par client', required=False, type=int),
        OpenApiParameter(name='min_rating', description='Note minimum', required=False, type=int),
        OpenApiParameter(name='max_rating', description='Note maximum', required=False, type=int),
        OpenApiParameter(name='ordering', description='Tri (ex: -created_at, rating)', required=False, type=str),
    ],
)
class ReviewListView(generics.ListAPIView):
    """
    Liste publique des avis visibles.
    """
    serializer_class = ReviewListSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']

    def get_queryset(self):
        queryset = Review.objects.filter(is_visible=True).select_related(
            'client', 'order', 'order__partner'
        )
        
        # Filtres personnalisés
        partner_id = self.request.query_params.get('partner')
        client_id = self.request.query_params.get('client')
        min_rating = self.request.query_params.get('min_rating')
        max_rating = self.request.query_params.get('max_rating')
        
        if partner_id:
            queryset = queryset.filter(order__partner_id=partner_id)
        if client_id:
            queryset = queryset.filter(client_id=client_id)
        if min_rating:
            queryset = queryset.filter(rating__gte=min_rating)
        if max_rating:
            queryset = queryset.filter(rating__lte=max_rating)
        
        return queryset


@extend_schema(
    tags=['reviews'],
    summary="Avis d'un partenaire",
    description="Retourne tous les avis d'un partenaire spécifique.",
)
class PartnerReviewListView(generics.ListAPIView):
    """
    Liste des avis d'un partenaire.
    """
    serializer_class = ReviewListSerializer

    def get_queryset(self):
        partner_id = self.kwargs.get('partner_id')
        return Review.objects.filter(
            order__partner_id=partner_id,
            is_visible=True
        ).select_related('client', 'order').order_by('-created_at')


@extend_schema(
    tags=['reviews'],
    summary="Créer un avis",
    description="Crée un nouvel avis (réservé aux clients).",
    request=ReviewCreateSerializer,
    responses={
        201: ReviewDetailSerializer,
        400: "Données invalides"
    }
)
class ReviewCreateView(generics.CreateAPIView):
    """
    Crée un nouvel avis.
    """
    serializer_class = ReviewCreateSerializer
    permission_classes = [permissions.IsAuthenticated, CanCreateReview]


@extend_schema(
    tags=['reviews'],
    summary="Détails d'un avis",
    description="Retourne les détails d'un avis spécifique.",
)
class ReviewDetailView(generics.RetrieveAPIView):
    """
    Détails d'un avis.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewDetailSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(
    tags=['reviews'],
    summary="Mettre à jour un avis",
    description="Met à jour un avis existant (réservé au propriétaire).",
    request=ReviewUpdateSerializer,
    responses={200: ReviewDetailSerializer}
)
class ReviewUpdateView(generics.UpdateAPIView):
    """
    Met à jour un avis.
    """
    queryset = Review.objects.all()
    serializer_class = ReviewUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsReviewOwnerOrReadOnly]


@extend_schema(
    tags=['reviews'],
    summary="Supprimer un avis",
    description="Supprime un avis (réservé au propriétaire ou admin).",
)
class ReviewDeleteView(generics.DestroyAPIView):
    """
    Supprime un avis.
    """
    queryset = Review.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsReviewOwnerOrReadOnly]


@extend_schema(
    tags=['reviews'],
    summary="Modérer un avis",
    description="Masquer/afficher un avis (admin uniquement).",
    request=ReviewModerateSerializer,
    responses={200: ReviewDetailSerializer}
)
class ReviewModerateView(generics.UpdateAPIView):
    """
    Modère un avis (admin uniquement).
    """
    queryset = Review.objects.all()
    serializer_class = ReviewModerateSerializer
    permission_classes = [permissions.IsAuthenticated, CanModerateReview]


@extend_schema(
    tags=['reviews'],
    summary="Statistiques globales",
    description="Retourne des statistiques sur les avis.",
)
class ReviewStatsView(APIView):
    """
    Statistiques globales des avis.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        reviews = Review.objects.filter(is_visible=True)
        
        # Statistiques générales
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Distribution des notes
        rating_dist = {}
        for i in range(1, 6):
            rating_dist[str(i)] = reviews.filter(rating=i).count()
        
        # Top reviewers
        top_reviewers = reviews.values(
            'client__id', 'client__first_name', 'client__last_name'
        ).annotate(
            review_count=Count('id'),
            avg_rating=Avg('rating')
        ).order_by('-review_count')[:5]
        
        # Top partners (les mieux notés)
        top_partners = Partner.objects.annotate(
            review_count=Count('orders__review', filter=Q(orders__review__is_visible=True)),
            avg_rating=Avg('orders__review__rating', filter=Q(orders__review__is_visible=True))
        ).filter(review_count__gt=0).order_by('-avg_rating')[:5]
        
        # Avis récents
        recent = reviews.order_by('-created_at')[:5]
        recent_serializer = ReviewListSerializer(recent, many=True)
        
        stats = {
            'total_reviews': total_reviews,
            'average_rating': round(avg_rating, 2),
            'rating_distribution': rating_dist,
            'top_reviewers': [
                {
                    'id': r['client__id'],
                    'name': f"{r['client__first_name']} {r['client__last_name']}",
                    'review_count': r['review_count'],
                    'avg_rating': round(r['avg_rating'], 2) if r['avg_rating'] else 0
                }
                for r in top_reviewers
            ],
            'top_partners': [
                {
                    'id': p.id,
                    'name': p.name,
                    'review_count': p.review_count,
                    'avg_rating': round(p.avg_rating, 2) if p.avg_rating else 0
                }
                for p in top_partners
            ],
            'recent_reviews': recent_serializer.data
        }
        
        serializer = ReviewStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)


@extend_schema(
    tags=['reviews'],
    summary="Statistiques d'un partenaire",
    description="Retourne les statistiques des avis pour un partenaire.",
)
class PartnerReviewStatsView(APIView):
    """
    Statistiques des avis d'un partenaire.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, partner_id):
        partner = get_object_or_404(Partner, id=partner_id)
        reviews = Review.objects.filter(order__partner=partner, is_visible=True)
        
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
        
        # Distribution des notes
        rating_dist = {}
        for i in range(1, 6):
            rating_dist[str(i)] = reviews.filter(rating=i).count()
        
        # Avis récents
        recent = reviews.order_by('-created_at')[:5]
        recent_serializer = ReviewListSerializer(recent, many=True)
        
        stats = {
            'partner_id': partner.id,
            'partner_name': partner.name,
            'total_reviews': total_reviews,
            'average_rating': round(avg_rating, 2),
            'rating_distribution': rating_dist,
            'recent_reviews': recent_serializer.data
        }
        
        serializer = PartnerReviewStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)


@extend_schema(
    tags=['reviews'],
    summary="Avis de l'utilisateur",
    description="Retourne les avis de l'utilisateur connecté.",
)
class MyReviewsView(generics.ListAPIView):
    """
    Liste des avis de l'utilisateur connecté.
    """
    serializer_class = ReviewListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Review.objects.filter(
            client=self.request.user
        ).select_related('order', 'order__partner').order_by('-created_at')


@extend_schema(
    tags=['reviews'],
    summary="Avis par commande",
    description="Vérifie si une commande a déjà un avis.",
)
class OrderReviewCheckView(APIView):
    """
    Vérifie si une commande a un avis.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        from apps.orders.models import Order
        
        order = get_object_or_404(Order, id=order_id, client=request.user)
        
        if hasattr(order, 'review'):
            review = order.review
            serializer = ReviewDetailSerializer(
                review,
                context={'request': request}
            )
            return Response({
                'has_review': True,
                'review': serializer.data
            })
        else:
            return Response({
                'has_review': False,
                'can_review': order.status == 'PICKED_UP'
            })