from django.urls import path
from . import views

app_name = 'partners'

urlpatterns = [
    # ========================================================================
    # CATEGORIES
    # ========================================================================
    
    path('categories/',
         views.CategoryPartnerListView.as_view(),
         name='category-list'),
    
    path('categories/<slug:slug>/',
         views.CategoryPartnerDetailView.as_view(),
         name='category-detail'),
    
    # ========================================================================
    # PARTNERS - LISTS AND SEARCH
    # ========================================================================
    
    path('',
         views.PartnerListView.as_view(),
         name='partner-list'),
    
    path('geo/',
         views.PartnerGeoListView.as_view(),
         name='partner-geo'),
    
    path('by-category/<int:category_id>/',
         views.PartnerByCategoryListView.as_view(),
         name='partner-by-category'),
    
    path('by-quarter/<str:quarter>/',
         views.PartnerByQuarterListView.as_view(),
         name='partner-by-quarter'),
    
    path('open-now/',
         views.PartnerOpenNowListView.as_view(),
         name='partner-open-now'),
    
    path('my-partners/',
         views.MyPartnersListView.as_view(),
         name='my-partners-list'),
    
    path('my-partners/<int:pk>/',
         views.MyPartnerDetailView.as_view(),
         name='my-partner-detail'),
    
    # ========================================================================
    # PARTNERS - CRUD
    # ========================================================================
    
    path('create/',
         views.PartnerCreateView.as_view(),
         name='partner-create'),
    
    # ⚠️ Attention: l'ordre compte! Les paths spécifiques avant les génériques
    path('<int:pk>/offers/public/',           # Nouvel endpoint public
         views.PartnerOffersView.as_view(),
         name='partner-offers-public'),
    
    path('<int:partner_id>/offers/all/',      # Endpoint pour toutes les offres (auth required)
         views.PartnerOffersListView.as_view(),
         name='partner-offers-all'),
    
    path('<int:pk>/',
         views.PartnerDetailView.as_view(),
         name='partner-detail'),
    
    path('<int:pk>/update/',
         views.PartnerUpdateView.as_view(),
         name='partner-update'),
    
    path('<int:pk>/delete/',
         views.PartnerDeleteView.as_view(),
         name='partner-delete'),
    
    # ========================================================================
    # PARTNERS - SPECIFIC ACTIONS
    # ========================================================================
    
    path('<int:pk>/update-status/',
         views.PartnerStatusUpdateView.as_view(),
         name='partner-update-status'),
    
    # Gardez cet endpoint pour la compatibilité
    path('<int:pk>/offers/',                  
         views.PartnerOffersView.as_view(),
         name='partner-offers'),
    
    path('<int:pk>/check-availability/',
         views.PartnerAvailabilityCheckView.as_view(),
         name='partner-check-availability'),
    
    path('<int:pk>/stats/',
         views.PartnerStatsView.as_view(),
         name='partner-stats'),
]