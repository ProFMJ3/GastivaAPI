from django.db import models
from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import FoodOffer, FoodCategory
from .serializers import (
    FoodCategorySerializer, FoodCategoryDetailSerializer,
    FoodOfferListSerializer, FoodOfferDetailSerializer,
    FoodOfferCreateUpdateSerializer, FoodOfferStatusUpdateSerializer,
    FoodOfferReserveSerializer, FoodOfferStatsSerializer
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