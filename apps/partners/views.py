from django.db import models
from rest_framework import generics, permissions, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiParameter,OpenApiResponse
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
from apps.offers.serializers import FoodOfferListSerializer

from .filters import PartnerFilter
from .permissions import (
    IsPartnerOwnerOrReadOnly, CanCreatePartner,
    IsAdminForStatusUpdate, IsPartnerOwnerOrAdmin, IsPartner
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
    serializer_class = PartnerDetailSerializer
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
    @extend_schema(
        responses={200: FoodOfferListSerializer(many=True)}
    )

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
    @extend_schema(
        responses={200: OpenApiResponse(description="Disponibilité")}
    )

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
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        responses={200: OpenApiResponse(description="Statistiques")}
    )
    def get(self, request, pk):
        partner = get_object_or_404(Partner, pk=pk)

        # Vérifier que l'utilisateur a accès à ce partenaire
        if not request.user.is_staff and partner.owner != request.user:
            return Response(
                {'error': 'You do not have permission to view this partner\'s stats'},
                status=403
            )

        # Offers statistics
        from apps.offers.models import Offer
        total_offers = Offer.objects.filter(partner=partner).count()
        active_offers = Offer.objects.filter(partner=partner, status='ACTIVE').count()

        # Orders statistics
        from apps.orders.models import Order
        total_orders = Order.objects.filter(partner=partner).count()
        completed_orders = Order.objects.filter(
            partner=partner,
            status='PICKED_UP'
        ).count()

        # Revenue statistics
        from django.db.models import Sum
        completed_orders_qs = Order.objects.filter(
            partner=partner,
            status='PICKED_UP'
        )
        total_revenue = completed_orders_qs.aggregate(
            total=Sum('total_amount')
        )['total'] or 0

        # Revenue growth (comparison with previous period)
        # This is simplified - you might want more complex logic
        from django.utils import timezone
        from datetime import timedelta

        current_period = timezone.now() - timedelta(days=30)
        previous_period = current_period - timedelta(days=30)

        current_revenue = Order.objects.filter(
            partner=partner,
            status='PICKED_UP',
            updated_at__gte=current_period
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        previous_revenue = Order.objects.filter(
            partner=partner,
            status='PICKED_UP',
            updated_at__lt=current_period,
            updated_at__gte=previous_period
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        revenue_growth = 0
        if previous_revenue > 0:
            revenue_growth = ((current_revenue - previous_revenue) / previous_revenue * 100)

        # Waste statistics (estimates based on offers)
        # This is a simplified calculation - adjust based on your actual waste tracking
        from apps.offers.models import Offer
        total_waste_saved = 0
        for offer in Offer.objects.filter(partner=partner):
            # Assuming each saved offer prevents ~0.5kg of waste
            total_waste_saved += offer.total_sold * 0.5

        # Category sales distribution
        category_sales = {}
        for order in Order.objects.filter(partner=partner, status='PICKED_UP'):
            for item in order.items.all():
                category = item.offer.category.name if item.offer.category else 'Autres'
                if category not in category_sales:
                    category_sales[category] = 0
                category_sales[category] += item.quantity

        # Reviews statistics
        from apps.reviews.models import Review
        reviews = Review.objects.filter(order__partner=partner, is_visible=True)
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
            'revenue': {
                'total': total_revenue,
                'growth': round(revenue_growth, 1),
                'current_period': current_revenue,
                'previous_period': previous_revenue
            },
            'waste': {
                'total': round(total_waste_saved, 1),
                'growth': 15  # This should be calculated properly
            },
            'category_sales': category_sales,
            'reviews': {
                'total': total_reviews,
                'average_rating': round(float(avg_rating), 1),
                'distribution': rating_dist
            }
        })

@extend_schema(
    tags=['partner-offers'],
    summary="Get all offers for a partner",
    description="Returns all offers of a specific partner with active offers first in the list.",
    parameters=[
        OpenApiParameter(
            name='partner_id',
            type=int,
            location=OpenApiParameter.PATH,
            description='ID of the partner',
            required=True,
        ),
    ],
)
class PartnerOffersListView(generics.ListAPIView):
    """
    List all offers for a specific partner.
    Active offers are displayed first, followed by others.
    """
    serializer_class = FoodOfferListSerializer
    permission_classes = [permissions.IsAuthenticated, IsPartner]

    def get_queryset(self):
        partner_id = self.kwargs.get('partner_id')
        now = timezone.now()

        # Vérifier que l'utilisateur connecté est bien le propriétaire du partenaire
        # À adapter selon votre logique d'authentification
        if not self.request.user.partner_set.filter(id=partner_id).exists():
            return FoodOffer.objects.none()

        # Récupérer toutes les offres du partenaire
        queryset = FoodOffer.objects.filter(
            partner_id=partner_id
        ).select_related(
            'partner', 'category'
        ).annotate(
            # Annoter pour trier: les ACTIVES et non expirées en premier
            is_active_first=models.Case(
                models.When(
                    status=FoodOffer.Status.ACTIVE,
                    pickup_deadline__gt=now,
                    then=models.Value(0)
                ),
                default=models.Value(1),
                output_field=models.IntegerField()
            )
        ).order_by(
            'is_active_first',  # Les actives d'abord
            '-is_featured',      # Ensuite les mises en avant
            '-created_at'        # Enfin les plus récentes
        )

        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        
        # Récupérer le premier élément pour les infos du partenaire
        first_offer = queryset.first()
        
        if not first_offer:
            # Si pas d'offres, on retourne un objet vide avec les infos du partenaire
            # À adapter selon votre modèle Partner
            from partners.models import Partner
            try:
                partner = Partner.objects.get(id=self.kwargs.get('partner_id'))
                partner_name = partner.name
                partner_quarter = partner.quarter
                partner_logo = partner.logo.url if partner.logo else None
            except Partner.DoesNotExist:
                partner_name = None
                partner_quarter = None
                partner_logo = None
        else:
            partner_name = first_offer.partner.name
            partner_quarter = first_offer.partner.quarter
            partner_logo = first_offer.partner.logo.url if first_offer.partner.logo else None

        # Sérialiser les offres
        serializer = self.get_serializer(queryset, many=True)

        # Construire la réponse au format demandé
        response_data = {
            "partner_id": self.kwargs.get('partner_id'),
            "partner_name": partner_name,
            "partner_quarter": partner_quarter,
            "partner_logo": partner_logo,
            "total_offers": queryset.count(),
            "offers": serializer.data
        }

        return Response(response_data, status=status.HTTP_200_OK)