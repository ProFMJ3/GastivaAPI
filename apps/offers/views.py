from django.db import models
from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import F, extend_schema, OpenApiParameter
from django.db.models import Q, Count, Avg, ExpressionWrapper, FloatField
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.offers.pagination import StandardPagination

from .models import FoodOffer, FoodCategory
from .serializers import (
    FoodCategorySerializer, FoodCategoryDetailSerializer,
    FoodOfferListSerializer, FoodOfferDetailSerializer,
    FoodOfferCreateUpdateSerializer, FoodOfferStatusUpdateSerializer,
    FoodOfferReserveSerializer, FoodOfferStatsSerializer, PaginatedResponseSerializer
)
from .filters import FoodOfferFilter
from .permissions import IsOfferOwnerOrReadOnly, CanCreateOffer, IsOwnerOrAdmin
from apps.partners.models import Partner


# ============================================================================
# VIEWS FOR CATEGORIES
# ============================================================================

@extend_schema(
    tags=['offers'],
    summary="List categories",
    description="Return list of all active categories.",
)
class FoodCategoryListView(generics.ListAPIView):
    """
    GET: List of categories
    """
    queryset = FoodCategory.objects.filter(is_active=True)
    serializer_class = FoodCategorySerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=['offers'],
    summary="Category details",
    description="Return details of a category with its offers.",
)
class FoodCategoryDetailView(generics.RetrieveAPIView):
    """
    GET: Category details
    """
    queryset = FoodCategory.objects.all()
    serializer_class = FoodCategoryDetailSerializer
    lookup_field = 'slug'
    permission_classes = [permissions.AllowAny]


# ============================================================================
# VIEWS FOR OFFERS
# ============================================================================

@extend_schema(
    tags=['offers'],
    summary="List offers",
    description="Return list of available offers with filters.",
    parameters=[
        OpenApiParameter(name='category', description='Category ID', required=False, type=int),
        OpenApiParameter(name='partner', description='Partner ID', required=False, type=int),
        OpenApiParameter(name='quarter', description='Quarter', required=False, type=str),
        OpenApiParameter(name='min_price', description='Minimum price', required=False, type=float),
        OpenApiParameter(name='max_price', description='Maximum price', required=False, type=float),
        OpenApiParameter(name='is_available', description='Available only', required=False, type=bool),
        OpenApiParameter(name='is_featured', description='Featured only', required=False, type=bool),
        OpenApiParameter(name='search', description='Search by title', required=False, type=str),
    ],
)
class FoodOfferListView(generics.ListAPIView):
    """
    List all offers with advanced filters.
    """
    serializer_class = FoodOfferListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = FoodOfferFilter
    search_fields = ['title', 'description', 'partner__name']
    ordering_fields = ['discounted_price', 'pickup_deadline', 'created_at']
    ordering = ['-created_at']
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        """
        Filter queryset to show only active offers.
        """
        now = timezone.now()
        return FoodOffer.objects.select_related(
            'partner', 'category'
        ).filter(
            status=FoodOffer.Status.ACTIVE,
            pickup_deadline__gt=now
        )


@extend_schema(
    tags=['offers'],
    summary="Create offer",
    description="Create a new offer (reserved for partners).",
)
class FoodOfferCreateView(generics.CreateAPIView):
    """
    Create a new offer.
    """
    serializer_class = FoodOfferCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, CanCreateOffer]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(
    tags=['offers'],
    summary="Offer details",
    description="Return full details of an offer.",
)
class FoodOfferDetailView(generics.RetrieveAPIView):
    """
    Details of a specific offer.
    """
    queryset = FoodOffer.objects.all()
    serializer_class = FoodOfferDetailSerializer
    permission_classes = [permissions.AllowAny]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(
    tags=['offers'],
    summary="Update offer",
    description="Update an existing offer (reserved for owner).",
)
class FoodOfferUpdateView(generics.UpdateAPIView):
    """
    Update an offer.
    """
    queryset = FoodOffer.objects.all()
    serializer_class = FoodOfferCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


@extend_schema(
    tags=['offers'],
    summary="Delete offer",
    description="Delete an offer (reserved for owner or admin).",
)
class FoodOfferDeleteView(generics.DestroyAPIView):
    """
    Delete an offer.
    """
    queryset = FoodOffer.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]


@extend_schema(
    tags=['offers'],
    summary="Reserve offer",
    description="Reserve a quantity of an offer (for clients).",
    request=FoodOfferReserveSerializer,
)
class FoodOfferReserveView(APIView):
    """
    Reserve an offer.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        offer = get_object_or_404(FoodOffer, pk=pk)
        serializer = FoodOfferReserveSerializer(data=request.data)
        
        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']
            
            if offer.reserve(quantity):
                return Response({
                    'success': True,
                    'message': f'{quantity} item(s) reserved successfully.',
                    'remaining': offer.remaining_quantity
                })
            else:
                return Response({
                    'success': False,
                    'message': 'Cannot reserve this quantity.',
                    'available': offer.remaining_quantity
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['offers'],
    summary="Release reservation",
    description="Release a reservation (order cancellation).",
    request=FoodOfferReserveSerializer,
)
class FoodOfferReleaseView(APIView):
    """
    Release a reservation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        offer = get_object_or_404(FoodOffer, pk=pk)
        serializer = FoodOfferReserveSerializer(data=request.data)
        
        if serializer.is_valid():
            quantity = serializer.validated_data['quantity']
            offer.release_reservation(quantity)
            
            return Response({
                'success': True,
                'message': f'{quantity} item(s) released.',
                'remaining': offer.remaining_quantity
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['offers'],
    summary="Update status",
    description="Update offer status.",
    request=FoodOfferStatusUpdateSerializer,
)
class FoodOfferStatusUpdateView(APIView):
    """
    Update offer status.
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def patch(self, request, pk):
        offer = get_object_or_404(FoodOffer, pk=pk)
        serializer = FoodOfferStatusUpdateSerializer(offer, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            offer.update_status()
            offer.save()
            return Response(FoodOfferDetailSerializer(offer, context={'request': request}).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    tags=['offers'],
    summary="Featured offers",
    description="Return featured offers.",
)
class FoodOfferFeaturedListView(generics.ListAPIView):
    """
    List of featured offers.
    """
    serializer_class = FoodOfferListSerializer

    def get_queryset(self):
        now = timezone.now()
        return FoodOffer.objects.filter(
            is_featured=True,
            status=FoodOffer.Status.ACTIVE,
            pickup_deadline__gt=now
        ).select_related('partner', 'category')[:10]


@extend_schema(
    tags=['offers'],
    summary="Expiring soon",
    description="Return offers expiring in the next hours.",
    parameters=[
        OpenApiParameter(name='hours', description='Number of hours', required=False, type=int),
    ],
)
class FoodOfferExpiringSoonListView(generics.ListAPIView):
    """
    List of offers expiring soon.
    """
    serializer_class = FoodOfferListSerializer

    def get_queryset(self):
        hours = int(self.request.query_params.get('hours', 3))
        now = timezone.now()
        deadline = now + timezone.timedelta(hours=hours)
        
        return FoodOffer.objects.filter(
            status=FoodOffer.Status.ACTIVE,
            pickup_deadline__lte=deadline,
            pickup_deadline__gt=now
        ).select_related('partner', 'category').order_by('pickup_deadline')


@extend_schema(
    tags=['offers'],
    summary="Offers by partner",
    description="Return offers of a specific partner.",
)
class FoodOfferByPartnerListView(generics.ListAPIView):
    """
    List of offers by partner.
    """
    serializer_class = FoodOfferListSerializer

    def get_queryset(self):
        partner_id = self.kwargs.get('partner_id')
        now = timezone.now()
        
        return FoodOffer.objects.filter(
            partner_id=partner_id,
            status=FoodOffer.Status.ACTIVE,
            pickup_deadline__gt=now
        ).select_related('partner', 'category')


@extend_schema(
    tags=['offers'],
    summary="My partner offers",
    description="Return offers of my partners (for authenticated partner).",
)
class MyPartnerOffersListView(generics.ListAPIView):
    """
    List of offers from all partners owned by the current user.
    """
    serializer_class = FoodOfferListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        partner_ids = user.partners.values_list('id', flat=True)
        
        now = timezone.now()
        return FoodOffer.objects.filter(
            partner_id__in=partner_ids,
            pickup_deadline__gt=now
        ).select_related('partner', 'category').order_by('-created_at')


@extend_schema(
    tags=['offers'],
    summary="Statistics",
    description="Return statistics about offers.",
)
class FoodOfferStatsView(APIView):
    """
    Global statistics on offers.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        now = timezone.now()
        
        # Basic statistics
        total_offers = FoodOffer.objects.count()
        active_offers = FoodOffer.objects.filter(
            status=FoodOffer.Status.ACTIVE,
            pickup_deadline__gt=now
        ).count()
        
        # Most popular category
        popular_category = FoodCategory.objects.annotate(
            offer_count=Count('offers', filter=Q(offers__status='ACTIVE'))
        ).order_by('-offer_count').first()
        
        # Average discount
        from django.db.models import F, ExpressionField, FloatField
        avg_discount = FoodOffer.objects.filter(
            status='ACTIVE'
        ).annotate(
            discount=ExpressionField(
                (F('original_price') - F('discounted_price')) / F('original_price') * 100,
                output_field=FloatField()
            )
        ).aggregate(avg=Avg('discount'))['avg'] or 0
        
        stats = {
            'total_offers': total_offers,
            'active_offers': active_offers,
            'reserved_offers': FoodOffer.objects.filter(status='RESERVED').count(),
            'expired_offers': FoodOffer.objects.filter(status='EXPIRED').count(),
            'total_reserved': FoodOffer.objects.aggregate(
                total=models.Sum('quantity_reserved')
            )['total'] or 0,
            'average_discount': round(avg_discount, 2),
            'most_popular_category': {
                'id': popular_category.id if popular_category else None,
                'name': popular_category.name if popular_category else 'N/A',
                'offers_count': popular_category.offer_count if popular_category else 0
            } if popular_category else None
        }
        
        serializer = FoodOfferStatsSerializer(data=stats)
        serializer.is_valid()
        return Response(serializer.data)




@extend_schema(
    tags=['offers'],
    summary="Offres pour la page d'accueil",
    description="Endpoint public retournant les offres avec tous les filtres de la page d'accueil.",
    parameters=[
        # Filtre de recherche textuelle
        OpenApiParameter(name='search', description='Recherche par nom de plat ou restaurant', required=False, type=str),
        
        # Filtre de distance (simulé par quartier pour l'instant)
        OpenApiParameter(name='quarter', description='Filtrer par quartier', required=False, type=str),
        OpenApiParameter(name='distance_km', description='Filtrer par distance (simulé)', required=False, type=int),
        
        # Filtre urgent (expirant bientôt)
        OpenApiParameter(name='urgent', description='Offres expirant dans moins d\'1h', required=False, type=bool),
        OpenApiParameter(name='expiring_hours', description='Nombre d\'heures pour expirant (défaut: 1)', required=False, type=int),
        
        # Filtres par catégorie
        OpenApiParameter(name='category', description='ID de la catégorie', required=False, type=int),
        OpenApiParameter(name='category_slug', description='Slug de la catégorie', required=False, type=str),
        
        # Filtre par type de partenaire (via catégorie de partenaire)
        OpenApiParameter(name='partner_category', description='Catégorie de partenaire (restaurant, boulangerie, etc.)', required=False, type=str),
        
        # Filtre par prix
        OpenApiParameter(name='max_price', description='Prix maximum (ex: 1500)', required=False, type=int),
        OpenApiParameter(name='min_price', description='Prix minimum', required=False, type=int),
        
        # Options de tri
        OpenApiParameter(name='ordering', description='Tri: time_remaining, price, distance, popularity', required=False, type=str),
        
        # Pagination
        OpenApiParameter(name='page', description='Numéro de page', required=False, type=int),
        OpenApiParameter(name='page_size', description='Nombre d\'éléments par page (défaut: 20)', required=False, type=int),
    ],
    responses={
        200: PaginatedResponseSerializer(serializer=FoodOfferListSerializer),
        400: "Paramètres invalides"
    }
)
class HomeOffersView(generics.ListAPIView):
    """
    Endpoint public pour la page d'accueil avec tous les filtres.
    
    Filtres disponibles:
    - 🔍 Recherche textuelle (search)
    - 📍 Distance/Quartier (quarter, distance_km)
    - ⏰ Urgent (urgent, expiring_hours)
    - 🍽️ Catégories (category, category_slug, partner_category)
    - 💰 Prix (max_price, min_price)
    
    Tri disponible:
    - ⏱️ Temps restant (time_remaining)
    - 💵 Prix croissant (price)
    - 📏 Distance (distance)
    - ⭐ Popularité (popularity)
    """
    serializer_class = FoodOfferListSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = StandardPagination  # À définir selon votre configuration

    def get_queryset(self):
        # Base queryset: offres actives uniquement
        now = timezone.now()
        queryset = FoodOffer.objects.filter(
            status=FoodOffer.Status.ACTIVE,
            pickup_deadline__gt=now,
            available_from__lte=now,
            partner__status='APPROVED'  # Uniquement les partenaires approuvés
        ).select_related('partner', 'category')
        
        # ====================================================================
        # 1. FILTRE DE RECHERCHE TEXTUELLE
        # ====================================================================
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(partner__name__icontains=search)
            )
        
        # ====================================================================
        # 2. FILTRES DE DISTANCE / QUARTIER
        # ====================================================================
        quarter = self.request.query_params.get('quarter')
        if quarter:
            queryset = queryset.filter(partner__quarter__icontains=quarter)
        
        # Note: La distance réelle nécessiterait des coordonnées GPS
        # Pour l'instant, on simule avec le quartier
        distance_km = self.request.query_params.get('distance_km')
        if distance_km:
            # Cette partie serait à implémenter avec des calculs de distance
            # Si vous avez les coordonnées, vous pouvez filtrer par proximité
            pass
        
        # ====================================================================
        # 3. FILTRE URGENT (expirant bientôt)
        # ====================================================================
        urgent = self.request.query_params.get('urgent')
        if urgent and urgent.lower() == 'true':
            expiring_hours = int(self.request.query_params.get('expiring_hours', 1))
            urgent_deadline = now + timezone.timedelta(hours=expiring_hours)
            queryset = queryset.filter(pickup_deadline__lte=urgent_deadline)
        
        # ====================================================================
        # 4. FILTRES PAR CATÉGORIE
        # ====================================================================
        # Par ID de catégorie
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Par slug de catégorie
        category_slug = self.request.query_params.get('category_slug')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Par catégorie de partenaire (restaurant, boulangerie, etc.)
        partner_category = self.request.query_params.get('partner_category')
        if partner_category:
            queryset = queryset.filter(partner__category__slug=partner_category)
        
        # ====================================================================
        # 5. FILTRES DE PRIX
        # ====================================================================
        max_price = self.request.query_params.get('max_price')
        if max_price:
            try:
                max_price_value = float(max_price)
                queryset = queryset.filter(discounted_price__lte=max_price_value)
            except ValueError:
                pass
        
        min_price = self.request.query_params.get('min_price')
        if min_price:
            try:
                min_price_value = float(min_price)
                queryset = queryset.filter(discounted_price__gte=min_price_value)
            except ValueError:
                pass
        
        # ====================================================================
        # 6. TRI
        # ====================================================================
        ordering = self.request.query_params.get('ordering', '-created_at')
        
        if ordering == 'time_remaining':
            # Trier par deadline (plus proche d'abord)
            queryset = queryset.order_by('pickup_deadline')
        elif ordering == 'price':
            # Prix croissant
            queryset = queryset.order_by('discounted_price')
        elif ordering == '-price':
            # Prix décroissant
            queryset = queryset.order_by('-discounted_price')
        elif ordering == 'distance':
            # Trier par distance (à implémenter avec les coordonnées)
            # Par défaut, on trie par quartier
            queryset = queryset.order_by('partner__quarter')
        elif ordering == 'popularity':
            # Trier par popularité (nombre de réservations)
            queryset = queryset.annotate(
                popularity=Count('order_items')
            ).order_by('-popularity')
        elif ordering == 'discount':
            # Trier par pourcentage de réduction
            queryset = queryset.annotate(
                discount_percent=ExpressionWrapper(
                    (F('original_price') - F('discounted_price')) / F('original_price') * 100,
                    output_field=FloatField()
                )
            ).order_by('-discount_percent')
        else:
            # Tri par défaut (plus récent d'abord)
            queryset = queryset.order_by('-created_at')
        
        return queryset

    def list(self, request, *args, **kwargs):
        """Override list pour ajouter des métadonnées à la réponse."""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Pagination
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            response_data = self.get_paginated_response(serializer.data).data
        else:
            serializer = self.get_serializer(queryset, many=True)
            response_data = {
                'count': queryset.count(),
                'results': serializer.data
            }
        
        # Ajouter des métadonnées utiles pour le frontend
        response_data['filters_applied'] = {
            'search': request.query_params.get('search'),
            'quarter': request.query_params.get('quarter'),
            'urgent': request.query_params.get('urgent'),
            'max_price': request.query_params.get('max_price'),
            'category': request.query_params.get('category'),
            'ordering': request.query_params.get('ordering'),
        }
        
        # Ajouter des statistiques rapides
        response_data['quick_stats'] = {
            'total_offers': queryset.count(),
            'urgent_offers': queryset.filter(
                pickup_deadline__lte=timezone.now() + timezone.timedelta(hours=1)
            ).count() if not request.query_params.get('urgent') else None,
        }
        
        return Response(response_data)