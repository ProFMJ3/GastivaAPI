from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard principal
    path('partner/overview/',
         views.PartnerDashboardOverviewView.as_view(),
         name='partner-overview'),
    
    # Statistiques des offres
    path('partner/offers-stats/',
         views.PartnerOffersStatsView.as_view(),
         name='partner-offers-stats'),
    
    # Revenus par période
    path('partner/revenue/',
         views.PartnerRevenueView.as_view(),
         name='partner-revenue'),
]