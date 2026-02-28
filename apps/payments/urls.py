from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # ========================================================================
    # LISTES ET STATISTIQUES
    # ========================================================================
    # GET /api/payments/ - Liste des paiements
    path('',
         views.PaymentListView.as_view(),
         name='payment-list'),
    
    # GET /api/payments/stats/ - Statistiques
    path('stats/',
         views.PaymentStatsView.as_view(),
         name='payment-stats'),
    
    # GET /api/payments/check-balance/ - Vérifier solde
    path('check-balance/',
         views.PaymentBalanceCheckView.as_view(),
         name='payment-check-balance'),
    
    # ========================================================================
    # CRUD PAIEMENTS
    # ========================================================================
    # POST /api/payments/create/ - Créer un paiement
    path('create/',
         views.PaymentCreateView.as_view(),
         name='payment-create'),
    
    # GET /api/payments/<int:pk>/ - Détails d'un paiement
    path('<int:pk>/',
         views.PaymentDetailView.as_view(),
         name='payment-detail'),
    
    # PATCH /api/payments/<int:pk>/status/ - Mettre à jour statut (admin)
    path('<int:pk>/status/',
         views.PaymentStatusUpdateView.as_view(),
         name='payment-status'),
    
    # ========================================================================
    # ACTIONS SUR LES PAIEMENTS
    # ========================================================================
    # POST /api/payments/<int:pk>/process/ - Traiter le paiement
    path('<int:pk>/process/',
         views.PaymentProcessView.as_view(),
         name='payment-process'),
    
    # POST /api/payments/<int:pk>/refund/ - Rembourser (admin)
    path('<int:pk>/refund/',
         views.PaymentRefundView.as_view(),
         name='payment-refund'),
    
    # ========================================================================
    # PAIEMENT SPÉCIFIQUE À UNE COMMANDE
    # ========================================================================
    # POST /api/payments/order/<int:order_id>/ - Payer une commande
    path('order/<int:order_id>/',
         views.OrderPaymentView.as_view(),
         name='order-payment'),
]