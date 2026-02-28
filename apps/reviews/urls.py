from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    # ========================================================================
    # LISTES PUBLIQUES
    # ========================================================================
    # GET /api/reviews/ - Liste de tous les avis
    path('',
         views.ReviewListView.as_view(),
         name='review-list'),
    
    # GET /api/reviews/stats/ - Statistiques globales
    path('stats/',
         views.ReviewStatsView.as_view(),
         name='review-stats'),
    
    # GET /api/reviews/partner/<int:partner_id>/ - Avis d'un partenaire
    path('partner/<int:partner_id>/',
         views.PartnerReviewListView.as_view(),
         name='partner-reviews'),
    
    # GET /api/reviews/partner/<int:partner_id>/stats/ - Stats d'un partenaire
    path('partner/<int:partner_id>/stats/',
         views.PartnerReviewStatsView.as_view(),
         name='partner-review-stats'),
    
    # ========================================================================
    # AVIS UTILISATEUR
    # ========================================================================
    # GET /api/reviews/my-reviews/ - Mes avis
    path('my-reviews/',
         views.MyReviewsView.as_view(),
         name='my-reviews'),
    
    # GET /api/reviews/order/<int:order_id>/check/ - Vérifier avis par commande
    path('order/<int:order_id>/check/',
         views.OrderReviewCheckView.as_view(),
         name='order-review-check'),
    
    # ========================================================================
    # CRUD AVIS
    # ========================================================================
    # POST /api/reviews/create/ - Créer un avis
    path('create/',
         views.ReviewCreateView.as_view(),
         name='review-create'),
    
    # GET /api/reviews/<int:pk>/ - Détails d'un avis
    path('<int:pk>/',
         views.ReviewDetailView.as_view(),
         name='review-detail'),
    
    # PUT/PATCH /api/reviews/<int:pk>/update/ - Mettre à jour
    path('<int:pk>/update/',
         views.ReviewUpdateView.as_view(),
         name='review-update'),
    
    # DELETE /api/reviews/<int:pk>/delete/ - Supprimer
    path('<int:pk>/delete/',
         views.ReviewDeleteView.as_view(),
         name='review-delete'),
    
    # ========================================================================
    # MODÉRATION (ADMIN)
    # ========================================================================
    # PATCH /api/reviews/<int:pk>/moderate/ - Modérer
    path('<int:pk>/moderate/',
         views.ReviewModerateView.as_view(),
         name='review-moderate'),
]