from django.urls import path
from . import views

app_name = 'offers'

urlpatterns = [
    # ========================================================================
    # CATEGORIES
    # ========================================================================
    
    # GET /api/offers/categories/ - List categories
    path('categories/',
         views.FoodCategoryListView.as_view(),
         name='category-list'),
    
    # GET /api/offers/categories/<slug:slug>/ - Category details
    path('categories/<slug:slug>/',
         views.FoodCategoryDetailView.as_view(),
         name='category-detail'),
    
    # ========================================================================
    # OFFERS - LISTS AND SEARCH
    # ========================================================================
    
    # GET /api/offers/ - List offers
    path('',
         views.FoodOfferListView.as_view(),
         name='offer-list'),
    
    # GET /api/offers/featured/ - Featured offers
    path('featured/',
         views.FoodOfferFeaturedListView.as_view(),
         name='offer-featured'),
    
    # GET /api/offers/expiring-soon/ - Expiring soon
    path('expiring-soon/',
         views.FoodOfferExpiringSoonListView.as_view(),
         name='offer-expiring-soon'),
    
    # GET /api/offers/by-partner/<int:partner_id>/ - Offers by partner
    path('by-partner/<int:partner_id>/',
         views.FoodOfferByPartnerListView.as_view(),
         name='offer-by-partner'),
    
    # GET /api/offers/my-partner-offers/ - My partner offers
    path('my-partner-offers/',
         views.MyPartnerOffersListView.as_view(),
         name='my-partner-offers'),
    
    # GET /api/offers/stats/ - Statistics
    path('stats/',
         views.FoodOfferStatsView.as_view(),
         name='offer-stats'),
    
    # ========================================================================
    # OFFERS - CRUD
    # ========================================================================
    
    # POST /api/offers/create/ - Create offer
    path('create/',
         views.FoodOfferCreateView.as_view(),
         name='offer-create'),
    
    # GET /api/offers/<int:pk>/ - Offer details
    path('<int:pk>/',
         views.FoodOfferDetailView.as_view(),
         name='offer-detail'),
    
    # PUT/PATCH /api/offers/<int:pk>/update/ - Update offer
    path('<int:pk>/update/',
         views.FoodOfferUpdateView.as_view(),
         name='offer-update'),
    
    # DELETE /api/offers/<int:pk>/delete/ - Delete offer
    path('<int:pk>/delete/',
         views.FoodOfferDeleteView.as_view(),
         name='offer-delete'),
    
    # ========================================================================
    # OFFERS - SPECIFIC ACTIONS
    # ========================================================================
    
    # POST /api/offers/<int:pk>/reserve/ - Reserve
    path('<int:pk>/reserve/',
         views.FoodOfferReserveView.as_view(),
         name='offer-reserve'),
    
    # POST /api/offers/<int:pk>/release/ - Release reservation
    path('<int:pk>/release/',
         views.FoodOfferReleaseView.as_view(),
         name='offer-release'),
    
    # PATCH /api/offers/<int:pk>/update-status/ - Update status
    path('<int:pk>/update-status/',
         views.FoodOfferStatusUpdateView.as_view(),
         name='offer-update-status'),
]