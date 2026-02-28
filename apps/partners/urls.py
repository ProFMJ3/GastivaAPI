from django.urls import path
from . import views

app_name = 'partners'

urlpatterns = [
    # ========================================================================
    # CATEGORIES
    # ========================================================================
    
    # GET /api/partners/categories/ - List categories
    path('categories/',
         views.CategoryPartnerListView.as_view(),
         name='category-list'),
    
    # GET /api/partners/categories/<slug:slug>/ - Category details
    path('categories/<slug:slug>/',
         views.CategoryPartnerDetailView.as_view(),
         name='category-detail'),
    
    # ========================================================================
    # PARTNERS - LISTS AND SEARCH
    # ========================================================================
    
    # GET /api/partners/ - List partners
    path('',
         views.PartnerListView.as_view(),
         name='partner-list'),
    
    # GET /api/partners/geo/ - Geolocation data
    path('geo/',
         views.PartnerGeoListView.as_view(),
         name='partner-geo'),
    
    # GET /api/partners/by-category/<int:category_id>/ - Partners by category
    path('by-category/<int:category_id>/',
         views.PartnerByCategoryListView.as_view(),
         name='partner-by-category'),
    
    # GET /api/partners/by-quarter/<str:quarter>/ - Partners by quarter
    path('by-quarter/<str:quarter>/',
         views.PartnerByQuarterListView.as_view(),
         name='partner-by-quarter'),
    
    # GET /api/partners/open-now/ - Partners open now
    path('open-now/',
         views.PartnerOpenNowListView.as_view(),
         name='partner-open-now'),
    
    # GET /api/partners/my-partner/ - My partner
   path('my-partners/',                    # Liste de mes partenaires
         views.MyPartnersListView.as_view(),
         name='my-partners-list'),
    
    path('my-partners/<int:pk>/',           # Détail d'un de mes partenaires
         views.MyPartnerDetailView.as_view(),
         name='my-partner-detail'),
    # ========================================================================
    # PARTNERS - CRUD
    # ========================================================================
    
    # POST /api/partners/create/ - Create partner
    path('create/',
         views.PartnerCreateView.as_view(),
         name='partner-create'),
    
    # GET /api/partners/<int:pk>/ - Partner details
    path('<int:pk>/',
         views.PartnerDetailView.as_view(),
         name='partner-detail'),
    
    # PUT/PATCH /api/partners/<int:pk>/update/ - Update partner
    path('<int:pk>/update/',
         views.PartnerUpdateView.as_view(),
         name='partner-update'),
    
    # DELETE /api/partners/<int:pk>/delete/ - Delete partner
    path('<int:pk>/delete/',
         views.PartnerDeleteView.as_view(),
         name='partner-delete'),
    
    # ========================================================================
    # PARTNERS - SPECIFIC ACTIONS
    # ========================================================================
    
    # PATCH /api/partners/<int:pk>/update-status/ - Change status (admin)
    path('<int:pk>/update-status/',
         views.PartnerStatusUpdateView.as_view(),
         name='partner-update-status'),
    
    # GET /api/partners/<int:pk>/offers/ - Partner offers
    path('<int:pk>/offers/',
         views.PartnerOffersView.as_view(),
         name='partner-offers'),
    
    # GET /api/partners/<int:pk>/check-availability/ - Check availability
    path('<int:pk>/check-availability/',
         views.PartnerAvailabilityCheckView.as_view(),
         name='partner-check-availability'),
    
    # GET /api/partners/<int:pk>/stats/ - Partner statistics
    path('<int:pk>/stats/',
         views.PartnerStatsView.as_view(),
         name='partner-stats'),
]