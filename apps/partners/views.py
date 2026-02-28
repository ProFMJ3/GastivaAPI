from django.db import models
from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import CategoryPartner, Partner
from .serializers import (
    CategoryPartnerSerializer, CategoryPartnerDetailSerializer,
    PartnerListSerializer, PartnerDetailSerializer,
    PartnerCreateUpdateSerializer, PartnerStatusUpdateSerializer,
    PartnerGeoSerializer
)
from .filters import PartnerFilter
from .permissions import (
    IsPartnerOwnerOrReadOnly, CanCreatePartner,
    IsAdminForStatusUpdate, IsPartnerOwnerOrAdmin
)


# ============================================================================
# VIEWS FOR PARTNER CATEGORIES
# ============================================================================

@extend_schema(
    tags=['categories'],
    summary="List categories",
    description="Return list of partner categories."
)
class CategoryPartnerListView(generics.ListAPIView):
    """
    List of partner categories.
    """
    queryset = CategoryPartner.objects.filter(is_active=True)
    serializer_class = CategoryPartnerSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(
    tags=['categories'],
    summary="Category details",
    description="Return details of a category with its partners."
)
class CategoryPartnerDetailView(generics.RetrieveAPIView):
    """
    Category details.
    """
    queryset = CategoryPartner.objects.filter(is_active=True)
    serializer_class = CategoryPartnerDetailSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


# ============================================================================
# VIEWS FOR PARTNERS - LISTS
# ============================================================================

@extend_schema(
    tags=['partners'],
    summary="List partners",
    description="Return list of partners with filters.",
    parameters=[
        OpenApiParameter(name='category', description='Category ID', required=False, type=int),
        OpenApiParameter(name='quarter', description='Filter by quarter', required=False, type=str),
        OpenApiParameter(name='city', description='Filter by city', required=False, type=str),
        OpenApiParameter(name='search', description='Search by name', required=False, type=str),
        OpenApiParameter(name='open_now', description='Open now', required=False, type=bool),
        OpenApiParameter(name='status', description='Status (admin)', required=False, type=str),
    ],
)
class PartnerListView(generics.ListAPIView):
    """
    List of partners with advanced filters.
    """
    serializer_class = PartnerListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PartnerFilter
    search_fields = ['name', 'description', 'quarter', 'address']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        
        # Admins see all, others see only approved
        if user.is_authenticated and user.role == 'ADMIN':
            return Partner.objects.all().select_related('category', 'owner')
        else:
            return Partner.objects.filter(
                status=Partner.Status.APPROVED
            ).select_related('category', 'owner')


@extend_schema(
    tags=['partners'],
    summary="Partners by category",
    description="Return partners of a specific category."
)
class PartnerByCategoryListView(generics.ListAPIView):
    """
    List of partners by category.
    """
    serializer_class = PartnerListSerializer

    def get_queryset(self):
        category_id = self.kwargs.get('category_id')
        return Partner.objects.filter(
            category_id=category_id,
            status=Partner.Status.APPROVED
        ).select_related('category', 'owner')


@extend_schema(
    tags=['partners'],
    summary="Partners by quarter",
    description="Return partners of a specific quarter."
)
class PartnerByQuarterListView(generics.ListAPIView):
    """
    List of partners by quarter.
    """
    serializer_class = PartnerListSerializer

    def get_queryset(self):
        quarter = self.kwargs.get('quarter')
        return Partner.objects.filter(
            quarter__icontains=quarter,
            status=Partner.Status.APPROVED
        ).select_related('category', 'owner')


@extend_schema(
    tags=['partners'],
    summary="Partners open now",
    description="Return partners currently open."
)
class PartnerOpenNowListView(generics.ListAPIView):
    """
    List of partners open now.
    """
    serializer_class = PartnerListSerializer

    def get_queryset(self):
        now = timezone.now()
        current_day = now.strftime('%A').lower()
        current_time = now.time()
        
        all_partners = Partner.objects.filter(
            status=Partner.Status.APPROVED
        ).select_related('category', 'owner')
        
        open_ids = []
        for partner in all_partners:
            if (current_day in partner.working_days and 
                partner.opening_time <= current_time <= partner.closing_time):
                open_ids.append(partner.id)
        
        return Partner.objects.filter(id__in=open_ids).select_related('category', 'owner')


@extend_schema(
    tags=['partners'],
    summary="Geolocation data",
    description="Simplified data for map display."
)
class PartnerGeoListView(generics.ListAPIView):
    """
    Geolocation data for map.
    """
    serializer_class = PartnerGeoSerializer

    def get_queryset(self):
        return Partner.objects.filter(
            status=Partner.Status.APPROVED,
            latitude__isnull=False,
            longitude__isnull=False
        ).select_related('category')


# ============================================================================
# VIEWS FOR PARTNERS - CRUD
# ============================================================================

@extend_schema(
    tags=['partners'],
    summary="Create partner",
    description="Create a new partner (reserved for users with PARTNER role)."
)
class PartnerCreateView(generics.CreateAPIView):
    """
    Create a new partner.
    """
    serializer_class = PartnerCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, CanCreatePartner]


@extend_schema(
    tags=['partners'],
    summary="Partner details",
    description="Return full details of a partner."
)
class PartnerDetailView(generics.RetrieveAPIView):
    """
    Partner details.
    """
    queryset = Partner.objects.all()
    serializer_class = PartnerDetailSerializer
    permission_classes = [permissions.AllowAny]



@extend_schema(
    tags=['partners'],
    summary="My partners",
    description="Return all partners of the authenticated user."
)
class MyPartnersListView(generics.ListAPIView):
    """
    List of partners belonging to the authenticated user.
    """
    serializer_class = PartnerListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Partner.objects.filter(
            owner=self.request.user
        ).select_related('category')


@extend_schema(
    tags=['partners'],
    summary="My partner detail",
    description="Return a specific partner of the authenticated user."
)
class MyPartnerDetailView(generics.RetrieveAPIView):
    """
    Detail of a specific partner belonging to the authenticated user.
    """
    serializer_class = PartnerDetailSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Partner.objects.filter(owner=self.request.user)


# Ou version simplifiée si vous voulez garder un seul endpoint
@extend_schema(
    tags=['partners'],
    summary="My partners",
    description="Return all partners of the authenticated user."
)
class MyPartnersView(APIView):
    """
    Get all partners of the authenticated user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        partners = Partner.objects.filter(owner=request.user)
        
        if not partners.exists():
            return Response(
                {"detail": "You don't have any partners."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Si un seul partenaire, retourner les détails complets
        if partners.count() == 1:
            serializer = PartnerDetailSerializer(partners.first())
        else:
            # Sinon, retourner la liste simplifiée
            serializer = PartnerListSerializer(partners, many=True)
        
        return Response(serializer.data)

@extend_schema(
    tags=['partners'],
    summary="Update partner",
    description="Update an existing partner (reserved for owner)."
)
class PartnerUpdateView(generics.UpdateAPIView):
    """
    Update a partner.
    """
    queryset = Partner.objects.all()
    serializer_class = PartnerCreateUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, IsPartnerOwnerOrReadOnly]


@extend_schema(
    tags=['partners'],
    summary="Delete partner",
    description="Delete a partner (reserved for owner or admin)."
)
class PartnerDeleteView(generics.DestroyAPIView):
    """
    Delete a partner.
    """
    queryset = Partner.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsPartnerOwnerOrAdmin]


# ============================================================================
# VIEWS FOR SPECIFIC ACTIONS
# ============================================================================

@extend_schema(
    tags=['partners'],
    summary="Update status",
    description="Update partner status (admin only)."
)
class PartnerStatusUpdateView(generics.UpdateAPIView):
    """
    Update partner status (admin).
    """
    queryset = Partner.objects.all()
    serializer_class = PartnerStatusUpdateSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]


@extend_schema(
    tags=['partners'],
    summary="Partner offers",
    description="Return active offers of a partner."
)
class PartnerOffersView(APIView):
    """
    Offers of a partner.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        partner = get_object_or_404(Partner, pk=pk)
        from apps.offers.serializers import FoodOfferListSerializer
        
        offers = partner.food_offers.filter(status='ACTIVE')
        serializer = FoodOfferListSerializer(offers, many=True)
        
        return Response({
            'partner_id': partner.id,
            'partner_name': partner.name,
            'total_offers': offers.count(),
            'offers': serializer.data
        })


@extend_schema(
    tags=['partners'],
    summary="Check availability",
    description="Check if partner is open at a given date/time.",
    parameters=[
        OpenApiParameter(name='date', description='Date (YYYY-MM-DD)', required=False, type=str),
        OpenApiParameter(name='time', description='Time (HH:MM)', required=False, type=str),
    ]
)
class PartnerAvailabilityCheckView(APIView):
    """
    Check partner availability.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        partner = get_object_or_404(Partner, pk=pk)
        
        date_str = request.query_params.get('date')
        time_str = request.query_params.get('time')
        
        now = timezone.now()
        
        if date_str and time_str:
            try:
                import datetime
                check_datetime = datetime.datetime.strptime(
                    f"{date_str} {time_str}", "%Y-%m-%d %H:%M"
                )
                check_datetime = timezone.make_aware(check_datetime)
                check_day = check_datetime.strftime('%A').lower()
                check_time = check_datetime.time()
            except ValueError:
                return Response(
                    {"error": "Invalid format. Use YYYY-MM-DD and HH:MM"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            check_day = now.strftime('%A').lower()
            check_time = now.time()
        
        is_open = (
            check_day in partner.working_days and
            partner.opening_time <= check_time <= partner.closing_time
        )
        
        return Response({
            'partner_id': partner.id,
            'partner_name': partner.name,
            'date': date_str or now.strftime('%Y-%m-%d'),
            'time': time_str or now.strftime('%H:%M'),
            'day': check_day,
            'is_open': is_open,
            'opening_time': partner.opening_time.strftime('%H:%M'),
            'closing_time': partner.closing_time.strftime('%H:%M'),
            'working_days': partner.get_working_days_display()
        })


@extend_schema(
    tags=['partners'],
    summary="Partner statistics",
    description="Return statistics about the partner."
)
class PartnerStatsView(APIView):
    """
    Partner statistics.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        partner = get_object_or_404(Partner, pk=pk)
        
        # Offers statistics
        total_offers = partner.food_offers.count()
        active_offers = partner.food_offers.filter(status='ACTIVE').count()
        
        # Orders statistics
        from apps.orders.models import Order
        total_orders = Order.objects.filter(partner=partner).count()
        completed_orders = Order.objects.filter(
            partner=partner, 
            status='PICKED_UP'
        ).count()
        
        # Reviews statistics
        from apps.reviews.models import Review
        reviews = Review.objects.filter(partner=partner, is_visible=True)
        total_reviews = reviews.count()
        avg_rating = reviews.aggregate(avg=models.Avg('rating'))['avg'] or 0
        
        # Rating distribution
        rating_dist = {}
        for i in range(1, 6):
            rating_dist[str(i)] = reviews.filter(rating=i).count()
        
        return Response({
            'partner_id': partner.id,
            'partner_name': partner.name,
            'offers': {
                'total': total_offers,
                'active': active_offers
            },
            'orders': {
                'total': total_orders,
                'completed': completed_orders
            },
            'reviews': {
                'total': total_reviews,
                'average_rating': round(float(avg_rating), 1),
                'distribution': rating_dist
            }
        })